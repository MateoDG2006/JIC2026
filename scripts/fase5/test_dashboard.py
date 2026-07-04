#!/usr/bin/env python
"""Smoke test del visor GNN (JIC). Analytics ChEMBL → ``proyecto analisis/viz/``."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = [
    (ROOT / "outputs" / "models" / "best_gin_model.pt", "make train-gin"),
    (ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv", "make panama-predict"),
]


def main() -> int:
    missing = [(p, hint) for p, hint in REQUIRED if not p.exists()]
    if missing:
        print("Faltan artefactos GNN (opcional para dev local):")
        for p, hint in missing:
            print(f"  - {p}")
            print(f"    → {hint}")

    from viz.app import app  # noqa: F401
    from viz.services import inference

    print(f"GIN disponible: {inference.model_available()}")
    print("Analytics ChEMBL: cd 'proyecto analisis' && python viz/app.py")
    print("=== test-viz OK (GNN) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
