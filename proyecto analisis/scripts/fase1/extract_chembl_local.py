#!/usr/bin/env python
"""
Pipeline Flujo A — extracción ChEMBL offline (SQLite).

Pertenece a la **Fase 1 — Adquisición y extracción de datos** del proyecto de
analítica de datos. Genera ``data/raw/chembl_panama_bioactivity.csv`` a partir
de la base ``chembl_37.db`` (o vía API REST si se invoca con ``--backend api``).

Uso:
  python scripts/fase1/extract_chembl_local.py
  python scripts/fase1/extract_chembl_local.py --corpus-mode mida
  python scripts/fase1/extract_chembl_local.py --backend api
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_extract import (  # noqa: E402
    apply_quality_filters_from_config,
    build_bioactivity_table,
    build_mapping_table,
    load_chembl_config,
    load_corpus_compounds,
    resolve_corpus_mode,
    resolve_standard_types,
    summarize_extraction,
)
from src.analisis_proyecto.chembl_local import db_info, ensure_db_exists  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extracción ChEMBL — corpus panameño ampliado")
    parser.add_argument("--config", default=str(ROOT / "config" / "config.yaml"))
    parser.add_argument("--backend", choices=("sqlite", "api"), default=None)
    parser.add_argument(
        "--corpus-mode",
        choices=("full", "mida"),
        default=None,
        help="full: ~235 compuestos PubChem; mida: solo 20 ingredientes activos",
    )
    parser.add_argument("--corpus", default=str(ROOT / "data" / "raw" / "pubchem_panama_cids.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    cfg = load_chembl_config(args.config)
    backend = args.backend or cfg["backend"]
    corpus_mode = args.corpus_mode or resolve_corpus_mode(cfg)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    compounds_csv = out_dir / "chembl_corpus_compounds.csv"
    mapping_csv = out_dir / "chembl_corpus_mapping.csv"
    raw_csv = out_dir / "chembl_panama_bioactivity_raw.csv"
    clean_csv = out_dir / "chembl_panama_bioactivity.csv"

    print(f"Backend: {backend}")
    print(f"Corpus mode: {corpus_mode}")
    print(f"Standard types: {resolve_standard_types(cfg)}")
    if backend == "sqlite":
        db_path = ensure_db_exists(cfg["db_path"])
        info = db_info(db_path)
        size_gb = info["db_size_bytes"] / (1024**3)
        print(f"ChEMBLdb: {db_path} ({size_gb:.2f} GB)")

    print("\n1. Cargar compuestos del corpus...")
    compounds_df = load_corpus_compounds(args.corpus, mode=corpus_mode)
    compounds_df.to_csv(compounds_csv, index=False)
    n_mida = int(compounds_df.get("is_mida", False).sum()) if "is_mida" in compounds_df else 0
    print(f"   {len(compounds_df)} compuestos ({n_mida} MIDA) -> {compounds_csv}")

    print("\n2. Mapeo ChEMBL...")
    mapping_df = build_mapping_table(
        compounds_df,
        backend=backend,
        config_path=args.config,
        existing_mapping_path=mapping_csv,
        skip_resolved=True,
        verbose=True,
    )
    mapping_df.to_csv(mapping_csv, index=False)
    n_ok = mapping_df["match_status"].isin(["ok", "ambiguous"]).sum()
    print(f"   Match OK/ambiguo: {n_ok}/{len(mapping_df)} -> {mapping_csv}")

    print("\n3. Bioactividad raw...")
    raw_df = build_bioactivity_table(
        mapping_df,
        backend=backend,
        config_path=args.config,
        verbose=True,
    )
    raw_df.to_csv(raw_csv, index=False)
    print(f"   {len(raw_df):,} registros -> {raw_csv}")

    print("\n4. Filtros de calidad...")
    clean_df, stats_df = apply_quality_filters_from_config(raw_df, args.config)
    clean_df.to_csv(clean_csv, index=False)
    print(f"   {len(clean_df):,} conservados -> {clean_csv}")
    print(stats_df.to_string(index=False))

    summary = summarize_extraction(compounds_df, mapping_df, raw_df, clean_df)
    print("\nResumen por compuesto (top 15 por actividades clean):")
    top = summary.sort_values("n_activities_clean", ascending=False).head(15)
    print(top.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
