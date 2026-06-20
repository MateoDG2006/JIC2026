#!/usr/bin/env python
"""Smoke test del visor FastAPI unificado (GNN + analytics)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = [
    (ROOT / "data" / "processed" / "chembl_clean.csv", "make chembl-extract"),
    (ROOT / "data" / "processed" / "panama_distritos_merged.geojson", "make download-geodata"),
    (ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv", "make panama-predict"),
    (ROOT / "outputs" / "dashboard" / "model_eval.json", "make prepare-dashboard"),
    (ROOT / "outputs" / "chembl" / "models" / "rf_regressor.pkl", "entrenar modelos ChEMBL"),
]


def main() -> int:
    missing = [(p, hint) for p, hint in REQUIRED if not p.exists()]
    if missing:
        print("Faltan artefactos:")
        for p, hint in missing:
            print(f"  - {p}")
            print(f"    → {hint}")
        return 1

    from viz.app import app  # noqa: F401
    from viz.services.dashboard import load_chembl, load_geojson, load_toxicity_profile, predict_pchembl

    df = load_chembl()
    geo = load_geojson()
    tox = load_toxicity_profile()
    pred = predict_pchembl({
        "mw_freebase": 300, "alogp": 2.5, "psa": 50, "hba": 3, "hbd": 1,
        "aromatic_rings": 1, "heavy_atoms": 18, "rtb": 4, "num_ro5_violations": 0,
    })

    print(f"ChEMBL filas: {len(df)}")
    print(f"GeoJSON distritos: {len(geo['features'])}")
    print(f"Perfil toxicidad: {len(tox)} compuestos")
    print(f"Prediccion pChEMBL: {pred:.2f}")
    print("=== test-viz OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
