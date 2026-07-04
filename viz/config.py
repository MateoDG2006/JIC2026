"""Configuración central del visor GNN-Tox (FastAPI).

Define rutas absolutas a templates, static, corpus precomputado y modelo GIN.
Analytics ChEMBL vive en ``proyecto analisis/viz/`` (puerto 8001).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALISIS_ROOT = PROJECT_ROOT / "proyecto analisis"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
MODEL_PATH = PROJECT_ROOT / "outputs" / "models" / "best_gin_model.pt"
CORPUS_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

TOXICITY_PROFILE_CSV = PROJECT_ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv"
PANAMA_CIDS_CSV = PROJECT_ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
if not PANAMA_CIDS_CSV.is_file():
    PANAMA_CIDS_CSV = ANALISIS_ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
PANAMA_PROFILE_CSV = TOXICITY_PROFILE_CSV

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


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _viz_cfg() -> dict[str, Any]:
    return _load_yaml().get("viz", {})


def viz_host() -> str:
    return os.environ.get("VIZ_HOST") or _viz_cfg().get("host", "127.0.0.1")


def viz_port() -> int:
    return int(os.environ.get("VIZ_PORT") or _viz_cfg().get("port", 8000))
