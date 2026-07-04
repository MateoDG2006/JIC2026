"""Búsqueda de compuestos en PubChem por nombre (PUG REST).

Usado por el visor para resolver nombres comunes / IUPAC → CID, SMILES
e imagen de preview sin depender de SMILES manual del usuario.
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import requests

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
AUTOCOMPLETE_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete"
IMAGE_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

MAX_RETRIES = 3
RETRY_DELAY = 2.0
_NAME_LOOKUP_DELAY = 0.2

# Prefijos de 5 letras para autocomplete cuando el usuario escribe un solo carácter.
# PubChem no devuelve sugerencias con 1 letra; estos seeds amplían el pool por inicial.
SEEDS_BY_LETTER: dict[str, list[str]] = {
    "a": ["aspir", "atraz", "acety", "amino", "alcoh", "argin", "anili", "azole", "auran"],
    "b": ["benze", "bromo", "barbi", "bioti", "butan", "bruca", "boric", "baclo"],
    "c": ["chlor", "carbo", "cyan", "cyclo", "caffe", "cepha", "citri", "corti", "cipro"],
    "d": ["dexam", "dopam", "digit", "diclo", "doxor", "dextr", "diazep", "dinit"],
    "e": ["ethyl", "estra", "epine", "eryth", "eosin", "etopo", "estradi"],
    "f": ["fluor", "furos", "folic", "fenta", "formi", "flavo", "fenof"],
    "g": ["glyph", "gluco", "guani", "galla", "genta", "gluta", "griseo"],
    "h": ["hepar", "hydro", "halop", "histi", "hyosc", "hexan", "hydra"],
    "i": ["ibupr", "insul", "indom", "iodin", "imida", "isopr", "isoni"],
    "j": ["japon", "jasmo", "juniper", "jervi"],
    "k": ["keto", "kanam", "khell", "kaini"],
    "l": ["lysine", "lacto", "leuci", "lithi", "linco", "losar", "lutei"],
    "m": ["malat", "metho", "morph", "metfo", "manco", "micon", "melph"],
    "n": ["nicot", "nitro", "naphth", "norad", "neomy", "nalox", "nysta"],
    "o": ["oxida", "olanz", "ornit", "oxali", "octan", "oleic", "omepr"],
    "p": ["parac", "penic", "predn", "pyrid", "phosp", "propa", "pacli"],
    "q": ["quini", "querc", "quinol", "quina"],
    "r": ["ribof", "rifam", "reser", "ranit", "retino", "rutin", "rosuv"],
    "s": ["salic", "strep", "sulfa", "simva", "sertr", "sorbi", "stear"],
    "t": ["tebuc", "tetra", "thiaz", "tamox", "theop", "tolue", "trazo"],
    "u": ["uraci", "urea", "uridi", "ursod", "ubiqu"],
    "v": ["vanco", "verap", "vitam", "valpr", "vinbl", "vanil"],
    "w": ["warfa", "wortm", "willi"],
    "x": ["xylen", "xanth", "xenon"],
    "y": ["yohim", "yttri"],
    "z": ["zinco", "zolpi", "zeaxa", "zileu"],
}


def _get_with_retry(url: str, timeout: int = 60) -> requests.Response:
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.HTTPError) as exc:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise exc from None
    raise requests.RequestException("unreachable")


def _smiles_from_props(props: dict[str, Any]) -> str:
    for key in ("SMILES", "ConnectivitySMILES", "IsomericSMILES", "CanonicalSMILES"):
        value = props.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _compound_image_url(cid: int, size: int = 120) -> str:
    return f"{IMAGE_BASE}/{cid}/PNG?image_size={size}x{size}"


def _autocomplete_terms(query: str, limit: int) -> list[str]:
    """Sugerencias de nombres de compuesto vía autocomplete de PubChem."""
    url = f"{AUTOCOMPLETE_BASE}/compound/{quote(query, safe='')}/json"
    resp = requests.get(url, params={"limit": limit}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    terms = data.get("dictionary_terms", {}).get("compound", [])
    return [t for t in terms if isinstance(t, str) and t.strip()][:limit]


def _cid_from_name(name: str) -> int | None:
    """Resuelve un nombre de compuesto a su CID principal."""
    url = f"{BASE}/compound/name/{quote(name, safe='')}/cids/JSON"
    try:
        resp = _get_with_retry(url, timeout=20)
    except requests.RequestException:
        return None
    cids = resp.json().get("IdentifierList", {}).get("CID", [])
    if not cids:
        return None
    return int(cids[0])


def _properties_for_cids(cids: list[int]) -> dict[int, dict[str, Any]]:
    """Propiedades básicas en lote para una lista de CIDs."""
    if not cids:
        return {}

    cid_str = ",".join(str(c) for c in cids)
    url = (
        f"{BASE}/compound/cid/{cid_str}/property/"
        "Title,IUPACName,MolecularFormula,MolecularWeight,ConnectivitySMILES,SMILES/JSON"
    )
    try:
        resp = _get_with_retry(url, timeout=30)
    except requests.RequestException:
        return {}

    out: dict[int, dict[str, Any]] = {}
    for props in resp.json().get("PropertyTable", {}).get("Properties", []):
        cid = props.get("CID")
        if cid is None:
            continue
        smiles = _smiles_from_props(props)
        out[int(cid)] = {
            "title": props.get("Title") or "",
            "iupac_name": props.get("IUPACName") or "",
            "formula": props.get("MolecularFormula") or "",
            "molecular_weight": props.get("MolecularWeight"),
            "smiles": smiles,
        }
    return out


def _pool_terms_for_letter(letter: str) -> list[str]:
    """Amplía autocomplete con prefijos semilla para una sola letra."""
    return _cached_pool_terms_for_letter(letter.lower())


@lru_cache(maxsize=32)
def _cached_pool_terms_for_letter(letter: str) -> list[str]:
    seeds = SEEDS_BY_LETTER.get(letter, [f"{letter * 5}"])
    pool: list[str] = []
    seen: set[str] = set()

    for seed in seeds[:6]:
        try:
            for term in _autocomplete_terms(seed, limit=6):
                key = term.lower()
                if term.lower().startswith(letter) and key not in seen:
                    seen.add(key)
                    pool.append(term)
        except requests.RequestException:
            continue

    return pool


def _cids_from_esearch(prefix: str, max_records: int = 200) -> list[int]:
    """Fallback: CIDs vía E-utilities cuando el pool de nombres es insuficiente."""
    resp = requests.get(
        ESEARCH_URL,
        params={
            "db": "pccompound",
            "term": f"{prefix}*",
            "retmax": max_records,
            "retmode": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return [int(x) for x in resp.json().get("esearchresult", {}).get("idlist", [])]


def _build_results(
    cids: list[int],
    name_by_cid: dict[int, str],
) -> list[dict[str, Any]]:
    if not cids:
        return []

    props_map = _properties_for_cids(cids)
    results: list[dict[str, Any]] = []

    for cid in cids:
        props = props_map.get(cid, {})
        smiles = props.get("smiles") or ""
        if not smiles:
            continue
        display_name = props.get("title") or name_by_cid.get(cid, "")
        results.append({
            "cid": cid,
            "name": display_name,
            "search_term": name_by_cid.get(cid, ""),
            "iupac_name": props.get("iupac_name") or "",
            "formula": props.get("formula") or "",
            "molecular_weight": props.get("molecular_weight"),
            "smiles": smiles,
            "image_url": _compound_image_url(cid),
            "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        })

    return results


def _search_random_by_letter(letter: str, limit: int) -> list[dict[str, Any]]:
    """Compuestos aleatorios cuyos nombres empiezan con la letra dada."""
    letter = letter.strip().lower()
    if not letter or len(letter) != 1 or not letter.isalpha():
        return []

    terms = _pool_terms_for_letter(letter)
    if not terms:
        try:
            esearch_cids = _cids_from_esearch(letter)
            sampled = random.sample(esearch_cids, min(limit, len(esearch_cids)))
            return _build_results(sampled, {})
        except requests.RequestException:
            return []

    candidates = random.sample(terms, min(len(terms), limit + 8))

    seen_cids: set[int] = set()
    name_by_cid: dict[int, str] = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_cid_from_name, term): term for term in candidates}
        for future in as_completed(futures):
            term = futures[future]
            try:
                cid = future.result()
            except requests.RequestException:
                continue
            if cid is None or cid in seen_cids:
                continue
            seen_cids.add(cid)
            name_by_cid[cid] = term
            if len(seen_cids) >= limit + 4:
                for pending in futures:
                    pending.cancel()
                break

    if len(seen_cids) < limit:
        try:
            esearch_cids = _cids_from_esearch(letter)
            random.shuffle(esearch_cids)
            for cid in esearch_cids:
                if cid in seen_cids:
                    continue
                seen_cids.add(cid)
                if len(seen_cids) >= limit + 4:
                    break
        except requests.RequestException:
            pass

    if not seen_cids:
        return []

    sampled = random.sample(list(seen_cids), min(limit, len(seen_cids)))
    return _build_results(sampled, name_by_cid)


def search_compounds(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Busca compuestos por nombre en PubChem.

    Con 1 letra: devuelve ``limit`` compuestos aleatorios cuyo nombre empieza
    con esa inicial. Con 2+ caracteres: autocomplete + coincidencias directas.
    """
    query = query.strip()
    if not query:
        return []

    limit = max(1, min(limit, 20))

    if len(query) == 1:
        return _search_random_by_letter(query, limit)

    try:
        terms = _autocomplete_terms(query, limit)
    except requests.RequestException:
        terms = [query]

    if query.lower() not in {t.lower() for t in terms}:
        terms = [query] + terms

    seen_cids: set[int] = set()
    name_by_cid: dict[int, str] = {}

    for term in terms[:limit]:
        cid = _cid_from_name(term)
        time.sleep(_NAME_LOOKUP_DELAY)
        if cid is None or cid in seen_cids:
            continue
        seen_cids.add(cid)
        name_by_cid[cid] = term
        if len(seen_cids) >= limit:
            break

    return _build_results(list(seen_cids), name_by_cid)
