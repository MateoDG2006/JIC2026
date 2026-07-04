"""Catálogo del corpus panameño agrupado por familia química.

Carga ``data/raw/pubchem_panama_cids.csv`` (y nombres de
``outputs/reports/panama_pesticides_profile.csv`` si existe).
No incluye predicciones precomputadas: el visor ejecuta inferencia en vivo.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from typing import Any

from viz.config import PANAMA_CIDS_CSV, PANAMA_PROFILE_CSV

_cache: list[dict[str, Any]] | None = None

FAMILY_LABELS: dict[str, str] = {
    "Organophosphates": "Organofosforados",
    "Carbamates": "Carbamatos",
    "Triazines": "Triazinas",
    "Azole_fungicides": "Fungicidas azólicos",
    "Pyrethroids": "Piretroides",
    "Herbicides": "Herbicidas",
    "Fungicidas": "Fungicidas",
}

# Familia química para ingredientes activos del registro MIDA
MIDA_FAMILY_BY_NAME: dict[str, str] = {
    "Chlorpyrifos": "Organofosforados",
    "Malathion": "Organofosforados",
    "Dimethoate": "Organofosforados",
    "Methyl parathion": "Organofosforados",
    "Carbaryl": "Carbamatos",
    "Methomyl": "Carbamatos",
    "Aldicarb": "Carbamatos",
    "Atrazine": "Triazinas",
    "Simazine": "Triazinas",
    "Tebuconazole": "Fungicidas azólicos",
    "Propiconazole": "Fungicidas azólicos",
    "Difenoconazole": "Fungicidas azólicos",
    "Cypermethrin": "Piretroides",
    "Deltamethrin": "Piretroides",
    "Lambda-cyhalothrin": "Piretroides",
    "Glyphosate": "Herbicidas",
    "Paraquat": "Herbicidas",
    "2,4-D": "Herbicidas",
    "Mancozeb": "Fungicidas",
    "Chlorothalonil": "Fungicidas",
}

DISPLAY_NAMES_ES: dict[str, str] = {
    "Chlorpyrifos": "Clorpirifos",
    "Malathion": "Malatión",
    "Dimethoate": "Dimetoato",
    "Methyl parathion": "Paratión metílico",
    "Carbaryl": "Carbaril",
    "Methomyl": "Metomilo",
    "Aldicarb": "Aldicarb",
    "Atrazine": "Atrazina",
    "Simazine": "Simazina",
    "Tebuconazole": "Tebuconazol",
    "Propiconazole": "Propiconazol",
    "Difenoconazole": "Difenoconazol",
    "Cypermethrin": "Cipermetrina",
    "Deltamethrin": "Deltametrina",
    "Lambda-cyhalothrin": "Lambda-cihalotrina",
    "Glyphosate": "Glifosato",
    "Paraquat": "Paraquat",
    "2,4-D": "2,4-D",
    "Mancozeb": "Mancozeb",
    "Chlorothalonil": "Clorotalonil",
}

FAMILY_ORDER: list[str] = [
    "Organofosforados",
    "Carbamatos",
    "Triazinas",
    "Fungicidas azólicos",
    "Piretroides",
    "Herbicidas",
    "Fungicidas",
]

IMAGE_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid"


def _slugify(text: str, cid: int) -> str:
    base = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or f"cid-{cid}"


def _load_profile_names() -> dict[int, str]:
    if not PANAMA_PROFILE_CSV.is_file():
        return {}
    names: dict[int, str] = {}
    with PANAMA_PROFILE_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cid = int(row["cid"])
            except (KeyError, ValueError, TypeError):
                continue
            name = (row.get("compuesto") or "").strip()
            if name:
                names[cid] = name
    return names


def _resolve_family(raw_family: str, name_en: str, source: str) -> str:
    if source == "MIDA_name_search" and name_en in MIDA_FAMILY_BY_NAME:
        return MIDA_FAMILY_BY_NAME[name_en]
    if raw_family in FAMILY_LABELS:
        return FAMILY_LABELS[raw_family]
    if raw_family in FAMILY_LABELS.values():
        return raw_family
    return raw_family or "Sin clasificar"


def _display_name(name_en: str, cid: int, formula: str, profile_names: dict[int, str]) -> str:
    if name_en:
        return DISPLAY_NAMES_ES.get(name_en, name_en)
    if cid in profile_names:
        label = profile_names[cid]
        if label.startswith("CID_"):
            if formula:
                return f"{formula} (CID {cid})"
            return f"Compuesto CID {cid}"
        return label
    if formula:
        return f"{formula} (CID {cid})"
    return f"Compuesto CID {cid}"


def _load_compounds() -> list[dict[str, Any]]:
    global _cache
    if _cache is not None:
        return _cache

    if not PANAMA_CIDS_CSV.is_file():
        _cache = []
        return _cache

    profile_names = _load_profile_names()
    compounds: list[dict[str, Any]] = []
    seen_smiles: set[str] = set()

    with PANAMA_CIDS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            smiles = (row.get("SMILES_canonical") or row.get("SMILES") or "").strip()
            if not smiles or smiles in seen_smiles:
                continue
            seen_smiles.add(smiles)

            try:
                cid = int(row["CID"])
            except (KeyError, ValueError, TypeError):
                continue

            name_en = (row.get("name") or "").strip()
            source = (row.get("source") or "").strip()
            raw_family = (row.get("family") or "").strip()
            formula = (row.get("formula") or "").strip()
            family = _resolve_family(raw_family, name_en, source)
            display = _display_name(name_en, cid, formula, profile_names)

            compounds.append({
                "id": _slugify(name_en or display, cid),
                "cid": cid,
                "name": display,
                "name_en": name_en,
                "smiles": smiles,
                "formula": formula,
                "family": family,
                "source": source,
                "mida": source == "MIDA_name_search",
                "image_url": f"{IMAGE_BASE}/{cid}/PNG?image_size=80x80",
            })

    _cache = compounds
    return _cache


def list_compounds() -> list[dict[str, Any]]:
    """Lista plana de compuestos del corpus panameño."""
    return list(_load_compounds())


def list_by_family() -> list[dict[str, Any]]:
    """Compuestos agrupados por familia química (orden fijo)."""
    by_family: dict[str, list[dict[str, Any]]] = {}
    for compound in _load_compounds():
        by_family.setdefault(compound["family"], []).append(compound)

    for family in by_family:
        by_family[family].sort(key=lambda c: (not c["mida"], c["name"].lower()))

    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    for family in FAMILY_ORDER:
        if family in by_family:
            ordered.append({
                "family": family,
                "count": len(by_family[family]),
                "compounds": by_family[family],
            })
            seen.add(family)

    for family in sorted(by_family):
        if family not in seen:
            ordered.append({
                "family": family,
                "count": len(by_family[family]),
                "compounds": by_family[family],
            })

    return ordered


def get_compound(compound_id: str) -> dict[str, Any] | None:
    for compound in _load_compounds():
        if compound["id"] == compound_id:
            return compound
    return None


def reload_catalog() -> int:
    global _cache
    _cache = None
    return len(_load_compounds())
