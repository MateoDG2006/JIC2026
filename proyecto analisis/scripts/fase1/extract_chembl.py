#!/usr/bin/env python
"""
Pipeline Flujo A — extracción ChEMBL vía chembl-server.

Uso:
  make chembl-extract
  python scripts/fase1/extract_chembl.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.acquisition.extract import ChemblExtractor  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extracción ChEMBL — corpus panameño completo")
    parser.add_argument("--config", default=str(ROOT / "config" / "config.yaml"))
    parser.add_argument("--corpus", default=str(ROOT / "data" / "raw" / "pubchem_panama_cids.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    extractor = ChemblExtractor.from_config_file(args.config)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    compounds_csv = out_dir / "chembl_corpus_compounds.csv"
    mapping_csv = out_dir / "chembl_corpus_mapping.csv"
    raw_csv = out_dir / "chembl_panama_bioactivity_raw.csv"
    clean_csv = out_dir / "chembl_panama_bioactivity.csv"

    info = extractor.database.info()
    print(f"Backend: chembl-server ({extractor.config.require_server_url()})")
    print(f"Standard types: {extractor.standard_types()}")
    print(f"ChEMBLdb: {info.db_path} ({info.db_size_bytes / 1024**3:.2f} GB)")

    print("\nEjecutando pipeline ChEMBL...")
    result = extractor.run(
        args.corpus,
        existing_mapping_path=mapping_csv,
        skip_resolved=True,
        verbose=True,
    )

    result.compounds.to_csv(compounds_csv, index=False)
    result.mapping.to_csv(mapping_csv, index=False)
    result.raw.to_csv(raw_csv, index=False)
    result.clean.to_csv(clean_csv, index=False)

    n_mida = int(result.compounds.get("is_mida", False).sum()) if "is_mida" in result.compounds else 0
    n_ok = result.mapping["match_status"].isin(["ok", "ambiguous"]).sum()

    print(f"\n1. Compuestos: {len(result.compounds)} ({n_mida} MIDA) -> {compounds_csv}")
    print(f"2. Mapping OK/ambiguo: {n_ok}/{len(result.mapping)} -> {mapping_csv}")
    print(f"3. Bioactividad raw: {len(result.raw):,} -> {raw_csv}")
    print(f"4. Limpio: {len(result.clean):,} -> {clean_csv}")
    print(result.filter_stats.to_string(index=False))

    print("\nResumen por compuesto (top 15 por actividades clean):")
    top = result.summary.sort_values("n_activities_clean", ascending=False).head(15)
    print(top.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
