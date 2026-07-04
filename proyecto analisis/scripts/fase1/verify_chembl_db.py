#!/usr/bin/env python
"""Verifica conexión a chembl-server."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.acquisition.db import connect_chembl  # noqa: E402
from src.analisis_proyecto.acquisition.extract import ChemblConfigLoader  # noqa: E402


def main() -> int:
    cfg = ChemblConfigLoader.load()
    db = connect_chembl(cfg)
    info = db.info()
    print(f"OK: {cfg.require_server_url()}")
    print(f"  SQLite (contenedor): {info.db_path}")
    print(f"  Tamaño: {info.db_size_bytes / 1e9:.2f} GB")
    print(f"  Tablas: {', '.join(sorted(info.tables))}")
    if info.manifest:
        print(f"  Instalado: {info.manifest.get('installed_at')}")

    sample = db.fetch_activities(["CHEMBL463210"])
    print(f"  Prueba Chlorpyrifos: {len(sample)} actividades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
