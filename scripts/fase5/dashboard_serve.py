#!/usr/bin/env python3
"""Compatibilidad: redirige a ``scripts/fase4/viz_serve.py``.

El dashboard antiguo (Dash) vivía en ``dashboard/`` y se arrancaba con
``scripts/fase5/dashboard_serve.py``. Tras la refactorización (AUDIT P3/P12)
se unificó con el visor FastAPI bajo ``viz/`` — este shim mantiene los
``make`` antiguos funcionando sin romper.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "fase4" / "viz_serve.py"
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
