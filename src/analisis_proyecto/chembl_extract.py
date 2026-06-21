"""
Fachada unificada para extracción ChEMBL (Flujo A).

Decide a qué backend pegarle según ``config.yaml``:
    backend: sqlite   → dump local descargado (rápido, offline, ~50 GB)
    backend: api      → REST PUG (lento, online, sin dump)

Funciones públicas:
    load_chembl_config        — lee sección `chembl` del config + overrides ENV
    resolve_backend           — valida y normaliza el backend elegido
    resolve_standard_types    — IC50/EC50/Ki/... a buscar en ChEMBL
    resolve_corpus_mode       — `full` (235 compuestos) | `mida` (20 oficiales)
    build_mapping_table       — corpus PubChem → CHEMBL_ID (delega en backend)
    build_bioactivity_table   — CHEMBL_ID → filas de activity (delega)
    apply_quality_filters_*   — filtros pChEMBL/relation/validity_comment

Las funciones build_* son polimórficas en el backend, lo que permite
intercambiar SQLite vs API sin tocar los notebooks.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from src.analisis_proyecto.chembl_api import (
    STANDARD_TYPES,
    STANDARD_TYPES_EXPANDED,
    STANDARD_TYPES_NARROW,
    apply_quality_filters,
    build_bioactivity_table as build_bioactivity_table_api,
    build_mapping_table as build_mapping_table_api,
    load_corpus_compounds,
    load_mida_compounds,
    summarize_extraction,
)
from src.analisis_proyecto.chembl_local import (
    build_bioactivity_table_local,
    build_mapping_table_local,
    default_db_path,
    ensure_db_exists,
)

Backend = Literal["sqlite", "api"]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_chembl_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Lee sección `chembl` de config.yaml con overrides por variables de entorno."""
    defaults: dict[str, Any] = {
        "backend": os.environ.get("CHEMBL_BACKEND", "sqlite"),
        "version": os.environ.get("CHEMBL_VERSION", "37"),
        "db_path": os.environ.get("CHEMBL_DB_PATH") or str(default_db_path()),
        "ftp_url": (
            "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/"
            "chembl_37_sqlite.tar.gz"
        ),
        "pchembl_active_threshold": 6.0,
        "corpus_mode": os.environ.get("CHEMBL_CORPUS_MODE", "full"),
        "standard_types": list(STANDARD_TYPES_EXPANDED),
        "quality_filters": {
            "impute_pchembl": True,
            "require_exact_relation": True,
            "exclude_validity_comment": True,
        },
    }
    cfg_file = Path(config_path) if config_path else _project_root() / "config" / "config.yaml"
    if cfg_file.is_file():
        with cfg_file.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        chembl = raw.get("chembl") or {}
        defaults.update({k: v for k, v in chembl.items() if v is not None})
    if os.environ.get("CHEMBL_DB_PATH"):
        defaults["db_path"] = os.environ["CHEMBL_DB_PATH"]
    if os.environ.get("CHEMBL_BACKEND"):
        defaults["backend"] = os.environ["CHEMBL_BACKEND"]
    if os.environ.get("CHEMBL_CORPUS_MODE"):
        defaults["corpus_mode"] = os.environ["CHEMBL_CORPUS_MODE"]
    return defaults


def resolve_standard_types(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = config or load_chembl_config()
    raw = cfg.get("standard_types")
    if raw == "narrow":
        return STANDARD_TYPES_NARROW
    if isinstance(raw, (list, tuple)) and raw:
        return tuple(str(t) for t in raw)
    return STANDARD_TYPES


def resolve_corpus_mode(config: dict[str, Any] | None = None) -> str:
    cfg = config or load_chembl_config()
    mode = str(cfg.get("corpus_mode", "full")).lower()
    if mode not in ("full", "mida"):
        raise ValueError(f"corpus_mode inválido: {mode!r} (use 'full' o 'mida')")
    return mode


def resolve_quality_filters(config: dict[str, Any] | None = None) -> dict[str, bool]:
    cfg = config or load_chembl_config()
    defaults = {
        "impute_pchembl": True,
        "require_exact_relation": True,
        "exclude_validity_comment": True,
    }
    qf = cfg.get("quality_filters") or {}
    defaults.update({k: bool(v) for k, v in qf.items() if k in defaults})
    return defaults


def resolve_backend(backend: str | None = None, config: dict[str, Any] | None = None) -> Backend:
    cfg = config or load_chembl_config()
    chosen = (backend or cfg.get("backend", "sqlite")).lower()
    if chosen not in ("sqlite", "api"):
        raise ValueError(f"backend ChEMBL inválido: {chosen!r} (use 'sqlite' o 'api')")
    return chosen  # type: ignore[return-value]


def build_mapping_table(
    compounds_df: pd.DataFrame,
    *,
    backend: str | None = None,
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    cfg = load_chembl_config(config_path)
    mode = resolve_backend(backend, cfg)
    if mode == "sqlite":
        path = db_path or cfg["db_path"]
        ensure_db_exists(path)
        return build_mapping_table_local(compounds_df, path, **kwargs)
    return build_mapping_table_api(compounds_df, **kwargs)


def build_bioactivity_table(
    mapping_df: pd.DataFrame,
    *,
    backend: str | None = None,
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    cfg = load_chembl_config(config_path)
    mode = resolve_backend(backend, cfg)
    types = resolve_standard_types(cfg)
    if mode == "sqlite":
        path = db_path or cfg["db_path"]
        ensure_db_exists(path)
        kwargs.pop("sleep_s", None)
        kwargs.pop("enrich_metadata", None)
        kwargs.pop("fetch_molecule_from_chembl", None)
        return build_bioactivity_table_local(
            mapping_df, path, standard_types=types, **kwargs
        )
    return build_bioactivity_table_api(mapping_df, standard_types=types, **kwargs)


def apply_quality_filters_from_config(
    df: pd.DataFrame,
    config_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = load_chembl_config(config_path)
    return apply_quality_filters(df, **resolve_quality_filters(cfg))


__all__ = [
    "load_chembl_config",
    "resolve_backend",
    "resolve_standard_types",
    "resolve_corpus_mode",
    "resolve_quality_filters",
    "build_mapping_table",
    "build_bioactivity_table",
    "load_mida_compounds",
    "load_corpus_compounds",
    "apply_quality_filters",
    "apply_quality_filters_from_config",
    "summarize_extraction",
]
