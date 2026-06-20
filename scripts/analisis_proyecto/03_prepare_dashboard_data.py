#!/usr/bin/env python
"""Compatibilidad — delega a scripts/fase5/prepare_dashboard.py."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "fase5" / "prepare_dashboard.py"
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
