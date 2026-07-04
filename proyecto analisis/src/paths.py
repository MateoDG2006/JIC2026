"""Rutas del proyecto de análisis (ChEMBL)."""
from __future__ import annotations

import sys
from pathlib import Path

# Raíz de ``proyecto analisis/`` (padre de ``src/``)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = PROJECT_ROOT.parent


def setup_path() -> Path:
    """Añade PROJECT_ROOT a sys.path para imports ``from src....``."""
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return PROJECT_ROOT
