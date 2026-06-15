"""Configuracion central del servidor de visualizacion."""

from __future__ import annotations

import sys
from pathlib import Path

# Raiz del proyecto (un nivel arriba de viz/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Agregar src/ al path para importar modulos del modelo
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Rutas de datos y modelos
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_PATH = PROJECT_ROOT / "outputs" / "models" / "best_gin_model.pt"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
CORPUS_DIR = Path(__file__).resolve().parent / "data"

# Templates y estaticos
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

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
