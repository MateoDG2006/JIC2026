"""Carga de constantes ChEMBL desde JSON en ``config/chembl/``."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.paths import PROJECT_ROOT

CHEMBL_CONFIG_DIR = PROJECT_ROOT / "config" / "chembl"


@lru_cache(maxsize=16)
def _load(name: str) -> dict[str, Any]:
    path = CHEMBL_CONFIG_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Constante ChEMBL no encontrada: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def mida_registry_entries() -> tuple[dict[str, str], ...]:
    data = _load("mida_registry.json")
    return tuple(dict(e) for e in data["entries"])


def table_candidates() -> dict[str, tuple[str, ...]]:
    raw = _load("sqlite_schema.json")["table_candidates"]
    return {k: tuple(v) for k, v in raw.items()}


def column_aliases() -> dict[str, tuple[str, ...]]:
    raw = _load("sqlite_schema.json")["column_aliases"]
    return {k: tuple(v) for k, v in raw.items()}


def standard_types_narrow() -> tuple[str, ...]:
    return tuple(_load("standard_types.json")["narrow"])


def standard_types_expanded() -> tuple[str, ...]:
    return tuple(_load("standard_types.json")["expanded"])


def pchembl_active_threshold() -> float:
    return float(_load("standard_types.json")["pchembl_active_threshold"])


def binding_types() -> frozenset[str]:
    return frozenset(_load("standard_types.json")["binding_types"])


def organism_types() -> frozenset[str]:
    return frozenset(_load("standard_types.json")["organism_types"])


def min_potency_activities() -> int:
    return int(_load("standard_types.json").get("min_potency_activities", 3))


def reliability_tier(n_activities: int) -> str:
    """Confiabilidad del agregado de potencia por soporte de mediciones."""
    if n_activities >= 10:
        return "alto"
    if n_activities >= min_potency_activities():
        return "medio"
    return "bajo"


def units_to_molar() -> dict[str, float]:
    raw = _load("concentration_units.json")["units_to_molar"]
    return {k: float(v) for k, v in raw.items()}


def bioactivity_columns() -> tuple[str, ...]:
    return tuple(_load("columns.json")["bioactivity"])


def descriptor_columns() -> tuple[str, ...]:
    return tuple(_load("columns.json")["descriptor"])


def feature_columns() -> list[str]:
    return list(_load("columns.json")["feature"])


def multivariate_feature_columns() -> list[str]:
    return list(_load("columns.json")["multivariate_feature"])


def numeric_descriptor_columns() -> list[str]:
    cols = _load("columns.json")
    return list(cols["feature"]) + list(cols["numeric_descriptor_extra"])


def numeric_coerce_columns() -> tuple[str, ...]:
    return tuple(_load("columns.json")["numeric_coerce"])


def id_and_text_columns() -> frozenset[str]:
    return frozenset(_load("columns.json")["id_and_text"])


def categorical_columns() -> list[str]:
    return list(_load("columns.json")["categorical"])


def assay_feature_columns() -> list[str]:
    return list(_load("columns.json")["assay_feature"])
