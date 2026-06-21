#!/usr/bin/env python
"""Compatibilidad — delega a ``scripts/fase5/test_dashboard.py``.

Pertenece a la **Fase 5 — Integración y dashboard** del proyecto de analítica
de datos. Mantiene el comando antiguo de la parte "analítica" del curso, que
ahora comparte el smoke test con la Fase V del proyecto GIN.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "fase5" / "test_dashboard.py"
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
