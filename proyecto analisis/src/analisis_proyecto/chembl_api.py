"""
Cliente ChEMBL para el proyecto de análisis de datos (Flujo A).

Descarga bioactividad de los 20 ingredientes activos MIDA vía API REST
de ChEMBL (requests + reintentos). No usa chembl_webresource_client para
evitar fallos al cargar el schema /spore cuando el servidor EBI devuelve 500.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski

from src.data.mida import MIDA_ACTIVE_INGREDIENTS

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
MAX_RETRIES = 5
MAX_RETRIES_MAPPING = 2
RETRY_DELAY = 3.0
PAGE_LIMIT = 200
MAPPING_PAGE_LIMIT = 10
PAGE_SLEEP_S = 0.35

# IDs curados (registro local + mapeos validados). Evita consultas pesadas a la API.
KNOWN_MIDA_CHEMBL_IDS: dict[str, str] = {
    "Chlorpyrifos": "CHEMBL463210",
    "Malathion": "CHEMBL1200468",
    "Dimethoate": "CHEMBL1569524",
    "Methyl parathion": "CHEMBL346516",
    "Carbaryl": "CHEMBL46917",
    "Methomyl": "CHEMBL552761",
    "Aldicarb": "CHEMBL91732",
    "Atrazine": "CHEMBL15063",
    "Simazine": "CHEMBL5775",
    "Tebuconazole": "CHEMBL8937",
    "Propiconazole": "CHEMBL174240",
    "Difenoconazole": "CHEMBL91495",
    "Cypermethrin": "CHEMBL3033792",
    "Deltamethrin": "CHEMBL416",
    "Lambda-cyhalothrin": "CHEMBL64147",
    "Glyphosate": "CHEMBL9571438",
    "Paraquat": "CHEMBL13958",
    "2,4-D": "CHEMBL7715",
    "Mancozeb": "CHEMBL1200543",
    "Chlorothalonil": "CHEMBL468167",
}

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "Accept": "application/json",
        "User-Agent": "JIC2026-toxicity-panama/1.0 (academic; chembl_api)",
    }
)

RESOURCE_PLURAL = {
    "molecule": "molecules",
    "activity": "activities",
    "target": "targets",
    "assay": "assays",
}

# Familia química por ingrediente MIDA (el corpus PubChem marca todos como "mixed").
MIDA_FAMILY_MAP: dict[str, str] = {
    "Chlorpyrifos": "Organophosphates",
    "Malathion": "Organophosphates",
    "Dimethoate": "Organophosphates",
    "Methyl parathion": "Organophosphates",
    "Carbaryl": "Carbamates",
    "Methomyl": "Carbamates",
    "Aldicarb": "Carbamates",
    "Atrazine": "Triazines",
    "Simazine": "Triazines",
    "Tebuconazole": "Azole_fungicides",
    "Propiconazole": "Azole_fungicides",
    "Difenoconazole": "Azole_fungicides",
    "Cypermethrin": "Pyrethroids",
    "Deltamethrin": "Pyrethroids",
    "Lambda-cyhalothrin": "Pyrethroids",
    "Glyphosate": "Herbicides",
    "Paraquat": "Herbicides",
    "2,4-D": "Herbicides",
    "Mancozeb": "Fungicides",
    "Chlorothalonil": "Fungicides",
}

STANDARD_TYPES_NARROW = ("IC50", "EC50", "Ki")
STANDARD_TYPES_EXPANDED = (
    "IC50",
    "EC50",
    "Ki",
    "Kd",
    "Potency",
    "Inhibition",
    "AC50",
    "LC50",
    "GI50",
    "MIC",
    "LD50",
    "ED50",
    "IC90",
)
STANDARD_TYPES = STANDARD_TYPES_EXPANDED
PCHEMBL_ACTIVE_THRESHOLD = 6.0

# Conversión de unidades ChEMBL → concentración molar para pChEMBL = -log10(M)
_UNIT_TO_MOLAR: dict[str, float] = {
    "pm": 1e-12,
    "nm": 1e-9,
    "um": 1e-6,
    "µm": 1e-6,
    "μm": 1e-6,
    "mm": 1e-3,
    "cm": 1e-2,
    "m": 1.0,
}

MOLECULE_PROP_FIELDS = (
    "mw_freebase",
    "alogp",
    "psa",
    "hba",
    "hbd",
    "num_ro5_violations",
    "aromatic_rings",
    "heavy_atoms",
    "rtb",
    "molecular_species",
    "cx_logp",
    "cx_logd",
    "molecule_chembl_id",
    "pref_name",
    "molecule_structures",
)

ACTIVITY_FIELDS = (
    "activity_id",
    "molecule_chembl_id",
    "assay_chembl_id",
    "target_chembl_id",
    "standard_type",
    "standard_value",
    "standard_units",
    "standard_relation",
    "pchembl_value",
    "data_validity_comment",
    "potential_duplicate",
    "activity_comment",
    "assay_type",
    "bao_label",
)

BIOACTIVITY_COLUMNS = [
    "compound_name",
    "pubchem_cid",
    "chembl_id",
    "smiles",
    "family",
    "match_method",
    "activity_id",
    "assay_chembl_id",
    "target_chembl_id",
    "target_name",
    "target_type",
    "organism",
    "standard_type",
    "standard_value",
    "standard_units",
    "standard_relation",
    "pchembl_value",
    "pchembl_imputed",
    "activity_class",
    "activity_comment",
    "data_validity_comment",
    "potential_duplicate",
    "assay_type",
    "bao_label",
    "mw_freebase",
    "alogp",
    "psa",
    "hba",
    "hbd",
    "num_ro5_violations",
    "aromatic_rings",
    "heavy_atoms",
    "rtb",
    "molecular_species",
    "cx_logp",
    "cx_logd",
]


def _get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 60,
    max_retries: int | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """GET JSON con reintentos ante errores 5xx o de red."""
    retries = max_retries if max_retries is not None else MAX_RETRIES
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            if resp.status_code >= 500:
                resp.raise_for_status()
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, requests.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                wait = RETRY_DELAY * (attempt + 1)
                if not quiet:
                    print(
                        f"  [RETRY ChEMBL] {attempt + 1}/{retries}: {exc}. "
                        f"Reintentando en {wait:.0f}s..."
                    )
                time.sleep(wait)
    raise RuntimeError(f"ChEMBL API falló tras {retries} intentos: {last_error}")


def _fetch_paginated(
    resource: str,
    params: dict[str, Any],
    *,
    page_limit: int = PAGE_LIMIT,
    page_sleep_s: float = PAGE_SLEEP_S,
) -> list[dict[str, Any]]:
    """Descarga todas las páginas de un listado ChEMBL."""
    plural = RESOURCE_PLURAL[resource]
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        page_params = {**params, "limit": page_limit, "offset": offset}
        url = f"{CHEMBL_BASE}/{resource}.json"
        data = _get_json(url, params=page_params, timeout=90)
        batch = data.get(plural, [])
        rows.extend(batch)

        total = data.get("page_meta", {}).get("total_count", len(batch))
        offset += page_limit
        if not batch or offset >= total:
            break
        time.sleep(page_sleep_s)

    return rows


def _get_resource(
    resource: str,
    chembl_id: str,
    *,
    max_retries: int | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    url = f"{CHEMBL_BASE}/{resource}/{chembl_id}.json"
    return _get_json(url, max_retries=max_retries, quiet=quiet)


def _filter_molecules_limited(
    params: dict[str, Any],
    *,
    page_limit: int = MAPPING_PAGE_LIMIT,
    max_pages: int = 1,
) -> list[dict[str, Any]]:
    """Una o pocas páginas — suficiente para resolver ID sin miles de requests."""
    plural = RESOURCE_PLURAL["molecule"]
    rows: list[dict[str, Any]] = []
    offset = 0
    for _ in range(max_pages):
        page_params = {**params, "limit": page_limit, "offset": offset}
        data = _get_json(
            f"{CHEMBL_BASE}/molecule.json",
            params=page_params,
            timeout=45,
            max_retries=MAX_RETRIES_MAPPING,
            quiet=True,
        )
        batch = data.get(plural, [])
        rows.extend(batch)
        total = data.get("page_meta", {}).get("total_count", len(batch))
        offset += page_limit
        if not batch or offset >= total:
            break
    return rows


def _search_molecules(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Búsqueda por texto — endpoint ligero, 1 request."""
    data = _get_json(
        f"{CHEMBL_BASE}/molecule/search.json",
        params={"q": query, "limit": limit},
        timeout=45,
        max_retries=MAX_RETRIES_MAPPING,
        quiet=True,
    )
    return data.get("molecules", [])


def _match_result(
    chembl_id: str,
    method: str,
    status: str,
    n_candidates: int,
    pref_name: str | None = None,
) -> dict[str, Any]:
    return {
        "chembl_id": chembl_id,
        "match_method": method,
        "match_status": status,
        "n_candidates": n_candidates,
        "chembl_pref_name": pref_name,
    }


def canonicalize_smiles(smiles: str) -> str | None:
    """Devuelve SMILES canónico RDKit o None si es inválido."""
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _normalize_smiles_column(df: pd.DataFrame) -> pd.Series:
    """SMILES canónico RDKit; conserva el original si RDKit falla."""
    smiles_col = "SMILES_canonical" if "SMILES_canonical" in df.columns else "SMILES"
    raw = df[smiles_col].fillna(df.get("SMILES", ""))
    return raw.apply(lambda s: canonicalize_smiles(s) or (s if isinstance(s, str) else ""))


def load_mida_compounds(corpus_path: str | Path) -> pd.DataFrame:
    """
    Filtra los 20 ingredientes activos MIDA desde pubchem_panama_cids.csv.

    Returns:
        DataFrame con columnas: compound_name, pubchem_cid, smiles, family, source, is_mida
    """
    df = pd.read_csv(corpus_path)

    mida = df[
        (df["source"] == "MIDA_name_search")
        & (df["name"].isin(MIDA_ACTIVE_INGREDIENTS))
    ].copy()

    mida["compound_name"] = mida["name"]
    mida["pubchem_cid"] = mida["CID"]
    mida["smiles"] = _normalize_smiles_column(mida)
    mida["family"] = mida["compound_name"].map(MIDA_FAMILY_MAP).fillna("unknown")
    mida["is_mida"] = True

    out = mida[
        ["compound_name", "pubchem_cid", "smiles", "family", "source", "is_mida"]
    ].reset_index(drop=True)
    return out


def load_corpus_compounds(
    corpus_path: str | Path,
    *,
    mode: str = "full",
) -> pd.DataFrame:
    """
    Carga compuestos para extracción ChEMBL.

    mode:
        - ``full``: todo pubchem_panama_cids.csv con SMILES válido (~235)
        - ``mida``: solo los 20 ingredientes activos MIDA
    """
    if mode == "mida":
        return load_mida_compounds(corpus_path)

    df = pd.read_csv(corpus_path)
    work = df.copy()
    work["smiles"] = _normalize_smiles_column(work)
    valid = work[
        work["smiles"].notna() & (work["smiles"].astype(str).str.strip() != "")
    ].copy()

    def _compound_name(row: pd.Series) -> str:
        name = row.get("name")
        if pd.notna(name) and str(name).strip():
            return str(name).strip()
        return f"CID_{int(row['CID'])}"

    valid["compound_name"] = valid.apply(_compound_name, axis=1)
    valid["pubchem_cid"] = valid["CID"]
    valid["family"] = valid["family"].fillna("unknown")
    valid["source"] = valid["source"].fillna("unknown")
    valid["is_mida"] = valid.get("name", pd.Series(dtype=object)).isin(MIDA_ACTIVE_INGREDIENTS)

    return valid[
        ["compound_name", "pubchem_cid", "smiles", "family", "source", "is_mida"]
    ].reset_index(drop=True)


def _mapping_row_key(row: pd.Series | dict[str, Any]) -> str:
    if isinstance(row, pd.Series):
        return str(row["pubchem_cid"])
    return str(row["pubchem_cid"])


def _pick_best_match(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def score(mol: dict[str, Any]) -> tuple[int, int]:
        phase = mol.get("max_phase") or 0
        return (int(phase), 1 if mol.get("molecule_type") == "Small molecule" else 0)

    return max(candidates, key=score)


def resolve_chembl_id(
    compound_name: str,
    pubchem_cid: int | str,
    smiles: str,
    *,
    sleep_s: float = 0.2,
    use_known_registry: bool = True,
) -> dict[str, Any]:
    """
    Resuelve molecule_chembl_id con estrategia en cascada (API REST).

    Orden: registro local → búsqueda por nombre → pref_name/sinónimo (1 página).
    No usa xref PubChem (devuelve miles de hits y satura la API).
    """
    if use_known_registry and compound_name in KNOWN_MIDA_CHEMBL_IDS:
        chembl_id = KNOWN_MIDA_CHEMBL_IDS[compound_name]
        return _match_result(chembl_id, "known_registry", "ok", 1)

    time.sleep(sleep_s)

    # 1) Búsqueda por nombre (endpoint /molecule/search)
    for query in (compound_name, compound_name.lower()):
        try:
            candidates = _search_molecules(query, limit=10)
        except RuntimeError:
            candidates = []
        best = _pick_best_match(candidates)
        if best is not None:
            status = "ok" if len(candidates) == 1 else "ambiguous"
            return _match_result(
                best["molecule_chembl_id"],
                "search",
                status,
                len(candidates),
                best.get("pref_name"),
            )

    # 2) Filtros exactos — máximo 1 página, sin paginar miles de resultados
    for method, params in [
        ("pref_name", {"pref_name__iexact": compound_name}),
        ("synonym", {"molecule_synonyms__molecule_synonym__iexact": compound_name}),
    ]:
        time.sleep(sleep_s)
        try:
            candidates = _filter_molecules_limited(params, max_pages=1)
        except RuntimeError:
            continue
        best = _pick_best_match(candidates)
        if best is not None:
            status = "ok" if len(candidates) == 1 else "ambiguous"
            return _match_result(
                best["molecule_chembl_id"],
                method,
                status,
                len(candidates),
                best.get("pref_name"),
            )

    return {
        "chembl_id": None,
        "match_method": None,
        "match_status": "not_found",
        "n_candidates": 0,
        "chembl_pref_name": None,
    }


def props_from_smiles(smiles: str) -> dict[str, Any]:
    """Descriptores moleculares vía RDKit — sin llamada a ChEMBL."""
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    if mol is None:
        return {}
    return {
        "mw_freebase": Descriptors.MolWt(mol),
        "alogp": Crippen.MolLogP(mol),
        "psa": Descriptors.TPSA(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "hbd": Lipinski.NumHDonors(mol),
        "num_ro5_violations": None,
        "aromatic_rings": Lipinski.NumAromaticRings(mol),
        "heavy_atoms": Lipinski.HeavyAtomCount(mol),
        "rtb": Lipinski.NumRotatableBonds(mol),
        "molecular_species": None,
        "cx_logp": None,
        "cx_logd": None,
    }


def _lipinski_violations(mol) -> int:
    violations = 0
    if Descriptors.MolWt(mol) > 500:
        violations += 1
    if Crippen.MolLogP(mol) > 5:
        violations += 1
    if Lipinski.NumHDonors(mol) > 5:
        violations += 1
    if Lipinski.NumHAcceptors(mol) > 10:
        violations += 1
    return violations


def resolve_molecule_props(
    smiles: str,
    chembl_id: str | None = None,
    *,
    sleep_s: float = 0.15,
    fetch_from_chembl: bool = False,
) -> dict[str, Any]:
    """Propiedades desde RDKit (rápido). ChEMBL solo si fetch_from_chembl=True."""
    props = props_from_smiles(smiles)
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is not None:
        props["num_ro5_violations"] = _lipinski_violations(mol)

    if fetch_from_chembl and chembl_id:
        try:
            time.sleep(sleep_s)
            props.update(
                {
                    k: v
                    for k, v in fetch_molecule_properties(
                        chembl_id, sleep_s=0, max_retries=MAX_RETRIES_MAPPING, quiet=True
                    ).items()
                    if k in props and v is not None
                }
            )
        except RuntimeError:
            pass
    return props


def fetch_molecule_properties(
    chembl_id: str,
    *,
    sleep_s: float = 0.15,
    max_retries: int | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """Propiedades moleculares desde el endpoint molecule."""
    if sleep_s:
        time.sleep(sleep_s)
    mol = _get_resource(
        "molecule", chembl_id, max_retries=max_retries, quiet=quiet
    )
    props: dict[str, Any] = {"chembl_id": chembl_id}
    for field in MOLECULE_PROP_FIELDS:
        if field == "molecule_structures":
            struct = mol.get("molecule_structures") or {}
            props["smiles_chembl"] = struct.get("canonical_smiles")
        else:
            props[field] = mol.get(field)
    return props


def fetch_target_info(
    target_chembl_id: str,
    cache: dict[str, dict],
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    if not target_chembl_id:
        return {"target_name": None, "target_type": None, "organism": None}
    if target_chembl_id in cache:
        return cache[target_chembl_id]

    try:
        t = _get_resource(
            "target", target_chembl_id, max_retries=MAX_RETRIES_MAPPING, quiet=quiet
        )
        info = {
            "target_name": t.get("pref_name"),
            "target_type": t.get("target_type"),
            "organism": t.get("organism"),
        }
    except RuntimeError:
        info = {"target_name": None, "target_type": None, "organism": None}
    cache[target_chembl_id] = info
    return info


def fetch_assay_info(
    assay_chembl_id: str,
    cache: dict[str, dict],
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    if not assay_chembl_id:
        return {"assay_type": None, "bao_label": None}
    if assay_chembl_id in cache:
        return cache[assay_chembl_id]

    try:
        a = _get_resource(
            "assay", assay_chembl_id, max_retries=MAX_RETRIES_MAPPING, quiet=quiet
        )
        info = {
            "assay_type": a.get("assay_type"),
            "bao_label": a.get("bao_label"),
        }
    except RuntimeError:
        info = {"assay_type": None, "bao_label": None}
    cache[assay_chembl_id] = info
    return info


def fetch_activities_raw(
    chembl_id: str,
    *,
    sleep_s: float = 0.2,
    standard_types: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """
    Descarga actividades sin filtrar calidad.

    Consulta cada standard_type por separado para reducir timeouts/500 del servidor EBI.
    """
    types = standard_types or STANDARD_TYPES
    time.sleep(sleep_s)
    seen_ids: set[int | str] = set()
    records: list[dict[str, Any]] = []

    for stype in types:
        try:
            batch = _fetch_paginated(
                "activity",
                {
                    "molecule_chembl_id": chembl_id,
                    "standard_type": stype,
                },
            )
        except RuntimeError as exc:
            print(f"    [WARN] {chembl_id} / {stype}: {exc}")
            continue

        for record in batch:
            aid = record.get("activity_id")
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            records.append({field: record.get(field) for field in ACTIVITY_FIELDS})

    return records


def load_mapping_table(path: str | Path) -> pd.DataFrame | None:
    """Carga mapping previo si existe."""
    p = Path(path)
    if not p.exists():
        return None
    return pd.read_csv(p)


def build_mapping_table(
    compounds_df: pd.DataFrame,
    *,
    sleep_s: float = 0.2,
    verbose: bool = True,
    existing_mapping_path: str | Path | None = None,
    skip_resolved: bool = True,
) -> pd.DataFrame:
    """
    Resuelve ChEMBL ID para cada compuesto MIDA (incluye NaN si no hay match).

    Si `existing_mapping_path` existe y `skip_resolved=True`, reutiliza filas con
    chembl_id ya resuelto (evita repetir cientos de requests a la API).
    """
    existing: dict[str, dict[str, Any]] = {}
    if existing_mapping_path is not None:
        prev = load_mapping_table(existing_mapping_path)
        if prev is not None:
            for _, row in prev.iterrows():
                cid = row.get("chembl_id")
                if pd.notna(cid) and str(cid).strip():
                    existing[_mapping_row_key(row)] = row.to_dict()

    records: list[dict[str, Any]] = []
    for _, row in compounds_df.iterrows():
        key = _mapping_row_key(row)
        name = row["compound_name"]
        if skip_resolved and key in existing:
            if verbose:
                print(f"  {name}: reutilizado ({existing[key].get('chembl_id')})")
            records.append(existing[key])
            continue

        if verbose:
            print(f"  Mapeando: {name}")
        match = resolve_chembl_id(
            name,
            row["pubchem_cid"],
            row["smiles"],
            sleep_s=sleep_s,
        )
        records.append(
            {
                "compound_name": name,
                "pubchem_cid": row["pubchem_cid"],
                "smiles": row["smiles"],
                "family": row["family"],
                "chembl_id": match["chembl_id"],
                "match_method": match["match_method"],
                "match_status": match["match_status"],
                "n_candidates": match["n_candidates"],
                "chembl_pref_name": match["chembl_pref_name"],
            }
        )
    return pd.DataFrame(records)


def build_bioactivity_table(
    mapping_df: pd.DataFrame,
    *,
    sleep_s: float = 0.25,
    verbose: bool = True,
    enrich_metadata: bool = False,
    fetch_molecule_from_chembl: bool = False,
    standard_types: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """
    Construye tabla larga de bioactividad (versión raw).

    Por defecto es rápido:
    - Propiedades moleculares desde RDKit/SMILES (sin API molecule).
    - Sin consultas target/assay por fila (enrich_metadata=False).

    Con enrich_metadata=True se consultan target/assay por ID único (no por fila).
    """
    target_cache: dict[str, dict] = {}
    assay_cache: dict[str, dict] = {}
    all_rows: list[dict[str, Any]] = []

    for _, map_row in mapping_df.iterrows():
        name = map_row["compound_name"]
        chembl_id = map_row["chembl_id"]
        smiles = map_row["smiles"]

        if pd.isna(chembl_id) or not chembl_id:
            if verbose:
                print(f"  {name}: sin ChEMBL ID — 0 actividades")
            continue

        if verbose:
            print(f"  {name} ({chembl_id}): descargando actividades...")
        mol_props = resolve_molecule_props(
            smiles,
            str(chembl_id),
            sleep_s=sleep_s,
            fetch_from_chembl=fetch_molecule_from_chembl,
        )

        try:
            activities = fetch_activities_raw(
                chembl_id, sleep_s=sleep_s, standard_types=standard_types
            )
        except RuntimeError as exc:
            print(f"    [ERROR] {name}: {exc} — se omite este compuesto")
            continue

        if verbose:
            print(f"    → {len(activities)} registros raw")

        # Enriquecer metadatos una vez por ID único (no por cada fila)
        target_info_map: dict[str, dict] = {}
        assay_info_map: dict[str, dict] = {}
        if enrich_metadata and activities:
            for act in activities:
                tid = act.get("target_chembl_id")
                aid = act.get("assay_chembl_id")
                if tid and tid not in target_info_map:
                    target_info_map[tid] = fetch_target_info(tid, target_cache, quiet=True)
                if aid and aid not in assay_info_map:
                    assay_info_map[aid] = fetch_assay_info(aid, assay_cache, quiet=True)

        for act in activities:
            tid = act.get("target_chembl_id")
            aid = act.get("assay_chembl_id")
            target_info = target_info_map.get(tid, {}) if enrich_metadata else {}
            assay_info = assay_info_map.get(aid, {}) if enrich_metadata else {}

            row = {
                "compound_name": name,
                "pubchem_cid": map_row["pubchem_cid"],
                "chembl_id": chembl_id,
                "smiles": smiles,
                "family": map_row["family"],
                "match_method": map_row["match_method"],
                "activity_id": act.get("activity_id"),
                "assay_chembl_id": aid,
                "target_chembl_id": tid,
                "target_name": target_info.get("target_name"),
                "target_type": target_info.get("target_type"),
                "organism": target_info.get("organism"),
                "standard_type": act.get("standard_type"),
                "standard_value": act.get("standard_value"),
                "standard_units": act.get("standard_units"),
                "standard_relation": act.get("standard_relation"),
                "pchembl_value": act.get("pchembl_value"),
                "pchembl_imputed": False,
                "activity_comment": act.get("activity_comment"),
                "data_validity_comment": act.get("data_validity_comment"),
                "potential_duplicate": act.get("potential_duplicate"),
                "assay_type": act.get("assay_type") or assay_info.get("assay_type"),
                "bao_label": act.get("bao_label") or assay_info.get("bao_label"),
                "mw_freebase": mol_props.get("mw_freebase"),
                "alogp": mol_props.get("alogp"),
                "psa": mol_props.get("psa"),
                "hba": mol_props.get("hba"),
                "hbd": mol_props.get("hbd"),
                "num_ro5_violations": mol_props.get("num_ro5_violations"),
                "aromatic_rings": mol_props.get("aromatic_rings"),
                "heavy_atoms": mol_props.get("heavy_atoms"),
                "rtb": mol_props.get("rtb"),
                "molecular_species": mol_props.get("molecular_species"),
                "cx_logp": mol_props.get("cx_logp"),
                "cx_logd": mol_props.get("cx_logd"),
            }
            all_rows.append(row)

    if not all_rows:
        return pd.DataFrame(columns=BIOACTIVITY_COLUMNS)

    df = pd.DataFrame(all_rows)
    df = derive_activity_class(df)
    return df.reindex(columns=BIOACTIVITY_COLUMNS)


def compute_pchembl_from_standard_value(
    value: float | int | str | None,
    units: str | None,
) -> float | None:
    """Calcula pChEMBL = -log10(M) a partir de standard_value y standard_units."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    if not units:
        return None
    factor = _UNIT_TO_MOLAR.get(str(units).strip().lower())
    if factor is None:
        return None
    import math

    return -math.log10(numeric * factor)


def impute_pchembl_value(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rellena pchembl_value faltante cuando hay standard_value en unidades conocidas
    y standard_relation es '=' (medición puntual).
    """
    out = df.copy()
    if "pchembl_imputed" not in out.columns:
        out["pchembl_imputed"] = False

    pchembl = pd.to_numeric(out["pchembl_value"], errors="coerce")
    relation = out["standard_relation"].fillna("").astype(str)
    missing = pchembl.isna() & (relation == "=")

    if not missing.any():
        return out

    computed = out.loc[missing].apply(
        lambda r: compute_pchembl_from_standard_value(
            r.get("standard_value"), r.get("standard_units")
        ),
        axis=1,
    )
    imputed_mask = missing & computed.notna()
    out.loc[imputed_mask, "pchembl_value"] = computed[computed.notna()]
    out.loc[imputed_mask, "pchembl_imputed"] = True
    return out


def derive_activity_class(
    df: pd.DataFrame,
    threshold: float = PCHEMBL_ACTIVE_THRESHOLD,
) -> pd.DataFrame:
    """Añade activity_class: Active si pchembl_value >= 6, Inactive si < 6, NaN si falta."""
    out = df.copy()
    pchembl = pd.to_numeric(out["pchembl_value"], errors="coerce")
    out["activity_class"] = pd.Series(pd.NA, index=out.index, dtype="object")
    out.loc[pchembl >= threshold, "activity_class"] = "Active"
    out.loc[pchembl < threshold, "activity_class"] = "Inactive"
    return out


def apply_quality_filters(
    df: pd.DataFrame,
    *,
    impute_pchembl: bool = True,
    require_exact_relation: bool = True,
    exclude_validity_comment: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filtra registros de calidad para el dataset de análisis.

    Returns:
        (df_clean, stats_df) — stats_df documenta cuántos registros se excluyeron por regla.
    """
    work = impute_pchembl_value(df) if impute_pchembl else df.copy()
    n_start = len(work)

    rules: list[tuple[str, pd.Series]] = [
        (
            "pchembl_value nulo (tras imputación)",
            work["pchembl_value"].isna(),
        ),
    ]
    if require_exact_relation:
        rules.append(
            (
                "standard_relation != '='",
                work["standard_relation"].fillna("").astype(str) != "=",
            )
        )
    if exclude_validity_comment:
        rules.append(
            (
                "data_validity_comment no nulo",
                work["data_validity_comment"].notna()
                & (work["data_validity_comment"].astype(str).str.strip() != ""),
            )
        )

    stats: list[dict[str, Any]] = []
    excluded_mask = pd.Series(False, index=work.index)

    for label, mask in rules:
        n_flagged = int(mask.sum())
        stats.append(
            {
                "filtro": label,
                "registros_afectados": n_flagged,
                "pct_del_total": round(100 * n_flagged / n_start, 2) if n_start else 0.0,
            }
        )
        excluded_mask |= mask

    clean = work.loc[~excluded_mask].copy()
    stats.append(
        {
            "filtro": "TOTAL excluidos (unión de reglas)",
            "registros_afectados": int(excluded_mask.sum()),
            "pct_del_total": round(100 * excluded_mask.sum() / n_start, 2) if n_start else 0.0,
        }
    )
    stats.append(
        {
            "filtro": "TOTAL conservados",
            "registros_afectados": len(clean),
            "pct_del_total": round(100 * len(clean) / n_start, 2) if n_start else 0.0,
        }
    )
    stats_df = pd.DataFrame(stats)
    stats_df.attrs["n_raw"] = n_start
    stats_df.attrs["n_clean"] = len(clean)
    return clean, stats_df


def summarize_extraction(
    compounds_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
) -> pd.DataFrame:
    """Resumen por compuesto: match, actividades raw y limpias."""
    rows = []
    for _, comp in compounds_df.iterrows():
        name = comp["compound_name"]
        map_row = mapping_df.loc[mapping_df["compound_name"] == name].iloc[0]
        n_raw = len(raw_df[raw_df["compound_name"] == name]) if len(raw_df) else 0
        n_clean = len(clean_df[clean_df["compound_name"] == name]) if len(clean_df) else 0
        rows.append(
            {
                "compound_name": name,
                "family": comp["family"],
                "chembl_id": map_row["chembl_id"],
                "match_status": map_row["match_status"],
                "n_activities_raw": n_raw,
                "n_activities_clean": n_clean,
            }
        )
    return pd.DataFrame(rows)
