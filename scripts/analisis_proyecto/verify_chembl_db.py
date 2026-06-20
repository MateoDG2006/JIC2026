#!/usr/bin/env python
"""Verifica que ChEMBLdb SQLite esté instalada y el esquema sea compatible."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_extract import load_chembl_config
from src.analisis_proyecto.chembl_local import db_info, ensure_db_exists, fetch_activities_local


def main() -> int:
    cfg = load_chembl_config()
    path = ensure_db_exists(cfg["db_path"])
    info = db_info(path)
    print(f"OK: {path}")
    print(f"  Tamaño: {info['db_size_bytes'] / 1e9:.2f} GB")
    print(f"  Tablas: {', '.join(sorted(info['tables']))}")
    if info.get("manifest"):
        print(f"  Instalado: {info['manifest'].get('installed_at')}")

    sample = fetch_activities_local(["CHEMBL463210"], path)
    print(f"  Prueba Chlorpyrifos: {len(sample)} actividades IC50/EC50/Ki")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
