"""Figuras XAI GNN — visor JIC (proyecto hermano)."""
from __future__ import annotations

from pathlib import Path

from viz.config import PROJECT_ROOT


def xai_figures_dir() -> Path:
    return PROJECT_ROOT / "outputs" / "xai" / "figures"
