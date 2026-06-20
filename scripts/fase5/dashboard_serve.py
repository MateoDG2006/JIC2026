#!/usr/bin/env python3
"""Redirige a scripts/fase4/viz_serve.py — el dashboard vive en viz/."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "fase4" / "viz_serve.py"
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
