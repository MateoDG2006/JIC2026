#!/usr/bin/env python
"""
Pipeline Flujo D — geodatos Panamá (distritos + variables sociodemográficas).

Pertenece a la **Fase 6 — Geodatos y contexto Panamá** del proyecto de
analítica de datos. Construye ``data/processed/panama_distritos_merged.geojson``
con los 76 distritos y las 4 variables visualizadas en el mapa coroplético.

Uso:
  python scripts/analisis_proyecto/fase6/02_download_geodata.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.geodata_panama import build_panama_geodata  # noqa: E402


def main() -> int:
    raw_geojson = ROOT / "data" / "raw" / "panama_distritos.geojson"
    inec_csv = ROOT / "data" / "raw" / "inec_sociodemografico.csv"
    merged_geojson = ROOT / "data" / "processed" / "panama_distritos_merged.geojson"

    print("=== Flujo D — Descarga geodatos Panamá ===")
    report = build_panama_geodata(raw_geojson, inec_csv, merged_geojson)

    print(f"Distritos: {report['n_distritos']}")
    print(f"Provincias: {report['n_provincias']}")
    print(f"Sin match INEC: {report['distritos_sin_match_inec']}")
    print(f"Guardado: {report['raw_geojson']}")
    print(f"Guardado: {report['inec_csv']}")
    print(f"Guardado: {report['merged_geojson']}")

    manifest = ROOT / "data" / "processed" / "geodata_manifest.json"
    manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
