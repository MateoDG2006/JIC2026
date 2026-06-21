#!/usr/bin/env python
"""Compatibilidad — delega a ``scripts/fase5/prepare_dashboard.py``.

Pertenece a la **Fase 5 — Integración y dashboard** del proyecto de analítica
de datos. El módulo ``analisis_proyecto`` se introdujo para la parte de
"analítica de datos" del curso pero comparte el script de preparación con la
Fase V del proyecto GIN. Este shim ejecuta el mismo script bajo el nombre del
analisis_proyecto para no romper invocaciones existentes.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "fase5" / "prepare_dashboard.py"
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
