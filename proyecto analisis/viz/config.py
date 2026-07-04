"""Configuración del visor analytics ChEMBL."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

from src.paths import MONOREPO_ROOT, PROJECT_ROOT, setup_path

setup_path()

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "dashboard"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
CHEMBL_CSV = DATA_DIR / "compounds_features.csv"
CHEMBL_CSV_LEGACY = DATA_DIR / "chembl_clean.csv"
ACTIVITIES_CSV = DATA_DIR / "activities_clean.csv"
CHEMBL_MODELS_DIR = PROJECT_ROOT / "outputs" / "chembl" / "models"
CHEMBL_METRICS = PROJECT_ROOT / "outputs" / "chembl" / "results" / "stats_tests.csv"
GEOJSON_PATH = DATA_DIR / "panama_distritos_merged.geojson"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Perfil GNN (proyecto hermano JIC) — solo comparativa / mapa tóxico
TOXICITY_PROFILE_CSV = MONOREPO_ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv"
PANAMA_CIDS_CSV = PROJECT_ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
XAI_FIGURES_DIR = MONOREPO_ROOT / "outputs" / "xai" / "figures"

TASK_NAMES: list[str] = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-AtAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

MAP_VARIABLES: dict[str, str] = {
    "poblacion": "Población estimada",
    "superficie_agricola_ha": "Superficie agrícola (ha)",
    "indice_pobreza": "Índice de pobreza",
    "area_km2": "Área (km²)",
}

NUMERIC_COLS = [
    "pchembl_median", "pchembl_value", "mw_freebase", "alogp", "psa", "hba", "hbd",
    "aromatic_rings", "rtb", "num_ro5_violations", "standard_value",
]

FEATURE_LABELS: dict[str, str] = {
    "mw_freebase": "Peso molecular (MW)",
    "alogp": "LogP",
    "psa": "PSA",
    "hba": "HBA",
    "hbd": "HBD",
    "aromatic_rings": "Anillos aromáticos",
    "rtb": "Enlaces rotables",
    "num_ro5_violations": "Violaciones Lipinski",
}

PREDICTOR_NOTE = (
    "Proyecto descriptivo (Opción A): sin predictor pChEMBL. "
    "Ver Fase 4 §12 (docs/fases/fase4_modelado.md) y notebooks/fase4_modelado.ipynb §4."
)


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def use_bundle() -> bool:
    env = os.environ.get("DASHBOARD_BUNDLE", "").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return not CHEMBL_CSV.is_file() and (BUNDLE_DIR / "compounds_features.csv").is_file()


def resolve_path(canonical: Path, bundle_name: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_name
        if bundle_path.is_file():
            return bundle_path
    return canonical


def resolve_dir(canonical: Path, bundle_subdir: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_subdir
        if bundle_path.is_dir():
            return bundle_path
    return canonical


def viz_host() -> str:
    return os.environ.get("VIZ_ANALYTICS_HOST") or _load_yaml().get("viz", {}).get("host", "127.0.0.1")


def viz_port() -> int:
    return int(os.environ.get("VIZ_ANALYTICS_PORT") or _load_yaml().get("viz", {}).get("port", 8001))
