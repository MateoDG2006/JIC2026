"""Configuración central del visor GNN-Tox (FastAPI).

Define rutas absolutas a:
    - Código: ``templates/``, ``static/`` y corpus precomputado (``viz/data/``)
    - Datos canónicos: ``data/processed/``, ``outputs/models/``, ``outputs/dashboard/``
    - Bundle de despliegue: ``outputs/dashboard/bundle/`` para Render/Docker

Constantes Tox21:
    TASK_NAMES         — 12 dianas biológicas en orden DeepChem (AUDIT P5: definidas
                         localmente, sin importar src.data.dataset para que el visor
                         pueda iniciar aunque torch_geometric no esté instalado)
    TASK_DESCRIPTIONS  — etiquetas en español para mostrar en la UI

Constantes ChEMBL (UI):
    NUMERIC_COLS, FEATURE_LABELS, PREDICTOR_NOTE, MAP_VARIABLES

Funciones:
    use_bundle()        — True si se debe leer desde outputs/dashboard/bundle/
                          (modo despliegue cloud sin datos crudos)
    resolve_path(p, n)  — canónico o bundle según use_bundle()
    resolve_dir(p, n)   — análogo para directorios (xai/, models/)
    viz_host(), viz_port() — config de bind para uvicorn (env vars o config.yaml)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_PATH = PROJECT_ROOT / "outputs" / "models" / "best_gin_model.pt"
CORPUS_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Analytics — artefactos derivados y fuentes canonicas
ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "dashboard"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
CHEMBL_CSV = DATA_DIR / "chembl_clean.csv"
CHEMBL_MODELS_DIR = PROJECT_ROOT / "outputs" / "chembl" / "models"
CHEMBL_METRICS = PROJECT_ROOT / "outputs" / "chembl" / "results" / "metrics_summary.csv"
TOXICITY_PROFILE_CSV = PROJECT_ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv"
PANAMA_CIDS_CSV = PROJECT_ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
PANAMA_PROFILE_CSV = TOXICITY_PROFILE_CSV
GEOJSON_PATH = DATA_DIR / "panama_distritos_merged.geojson"
XAI_FIGURES_DIR = PROJECT_ROOT / "outputs" / "xai" / "figures"

# Orden canonico Tox21 — sin importar torch_geometric (AUDIT P5)
TASK_NAMES: list[str] = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-AtAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

TASK_DESCRIPTIONS: dict[str, str] = {
    "NR-AR": "Receptor de andrógenos",
    "NR-AR-LBD": "Dominio ligando AR",
    "NR-AhR": "Receptor aril-hidrocarburo",
    "NR-Aromatase": "Aromatasa (CYP19)",
    "NR-ER": "Receptor de estrógenos",
    "NR-ER-LBD": "Dominio ligando ER",
    "NR-PPAR-gamma": "Receptor PPAR-γ",
    "SR-ARE": "Estrés oxidativo (Nrf2)",
    "SR-AtAD5": "Daño al ADN",
    "SR-HSE": "Estrés por calor",
    "SR-MMP": "Membrana mitocondrial",
    "SR-p53": "Vía p53 (genotoxicidad)",
}

MAP_VARIABLES: dict[str, str] = {
    "poblacion": "Población estimada",
    "superficie_agricola_ha": "Superficie agrícola (ha)",
    "indice_pobreza": "Índice de pobreza",
    "area_km2": "Área (km²)",
}

NUMERIC_COLS = [
    "pchembl_value", "mw_freebase", "alogp", "psa", "hba", "hbd",
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
    "Solo se editan descriptores moleculares (8 features). "
    "Las features de ensayo/diana se completan con valores por defecto del perfil más frecuente."
)


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _viz_cfg() -> dict[str, Any]:
    return _load_yaml().get("viz", {})


def use_bundle() -> bool:
    env = os.environ.get("DASHBOARD_BUNDLE", "").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return not CHEMBL_CSV.is_file() and (BUNDLE_DIR / "chembl_clean.csv").is_file()


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
    return os.environ.get("VIZ_HOST") or _viz_cfg().get("host", "127.0.0.1")


def viz_port() -> int:
    return int(os.environ.get("VIZ_PORT") or _viz_cfg().get("port", 8000))
