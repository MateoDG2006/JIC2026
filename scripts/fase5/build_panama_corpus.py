#!/usr/bin/env python3
"""
Construye el corpus de plaguicidas panameños (Fase V).

Pipeline (ver docs/fase5_panama.md):
  1. PubChem Compound/name: ingredientes activos del MIDA → CID + SMILES
  2. PubChem Classification (HID 72): CIDs por familia de plaguicida
  3. PubChem Compound: SMILES en lotes para CIDs sin estructura
  4. RDKit: validación y canonicalización de SMILES
  5. PubChem Hazard (GHS): etiquetas regulatorias (validación externa)
  6. Featurizer: SMILES → grafos PyG → data/processed/panama_corpus.pt

Uso (desde la raíz del repo):
  python scripts/fase5/build_panama_corpus.py
  python scripts/fase5/build_panama_corpus.py --skip-ghs
  python scripts/fase5/build_panama_corpus.py --skip-pubchem
  python scripts/fase5/build_panama_corpus.py --skip-graphs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CIDS_CSV = ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
if not DEFAULT_CIDS_CSV.is_file():
    DEFAULT_CIDS_CSV = ROOT / "proyecto analisis" / "data" / "raw" / "pubchem_panama_cids.csv"
DEFAULT_GHS_CSV = ROOT / "data" / "raw" / "pubchem_ghs_labels.csv"
DEFAULT_GRAPHS_PT = ROOT / "data" / "processed" / "panama_corpus.pt"


def _smiles_column(df) -> str:
    if "SMILES_canonical" in df.columns:
        return "SMILES_canonical"
    return "SMILES"


def build_graphs_corpus(csv_path: Path, output_path: Path) -> dict[str, Any]:
    """Convierte el CSV enriquecido en grafos PyG y guarda panama_corpus.pt."""
    import pandas as pd
    import torch

    from src.data.featurizer import smiles_to_graph

    df = pd.read_csv(csv_path)
    smiles_col = _smiles_column(df)

    entries: list[tuple[str, Any]] = []
    failed = 0

    for _, row in df.iterrows():
        smiles = row.get(smiles_col, "")
        if not isinstance(smiles, str) or not smiles.strip():
            failed += 1
            continue

        graph = smiles_to_graph(smiles)
        if graph is None:
            failed += 1
            continue

        raw_name = row.get("name", "")
        if isinstance(raw_name, str) and raw_name.strip():
            name = raw_name.strip()
        else:
            name = f"CID_{int(row['CID'])}"

        graph.compound_name = name
        graph.cid = int(row["CID"])
        graph.family = str(row.get("family", ""))
        graph.source = str(row.get("source", ""))
        graph.smiles = smiles

        entries.append((name, graph))

    corpus: dict[str, Any] = {
        "entries": entries,
        "meta": {
            "n_csv_rows": len(df),
            "n_graphs": len(entries),
            "n_failed": failed,
            "source_csv": str(csv_path),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(corpus, output_path)
    return corpus


def print_summary(df, corpus: dict[str, Any] | None = None) -> None:
    """Imprime estadísticas del corpus construido."""
    mida_mask = df["source"] == "MIDA_name_search"
    n_mida = int(mida_mask.sum())

    print(f"\n{'=' * 60}")
    print("Resumen del corpus panameño")
    print(f"{'=' * 60}")
    print(f"  Compuestos totales (CSV):     {len(df)}")
    print(f"  Ingredientes MIDA (por nombre): {n_mida}")

    if "family" in df.columns:
        families = df["family"].value_counts()
        print("  Por familia:")
        for fam, count in families.items():
            print(f"    {fam}: {count}")

    if corpus is not None:
        meta = corpus["meta"]
        print(f"  Grafos PyG guardados:         {meta['n_graphs']}")
        if meta["n_failed"]:
            print(f"  SMILES sin grafo:             {meta['n_failed']}")

    print(f"{'=' * 60}")


def run_pubchem_pipeline(
    cids_csv: Path,
    ghs_csv: Path,
    *,
    skip_ghs: bool,
) -> Any:
    """Ejecuta los pasos 1–3 (o 1–5) del pipeline PubChem."""
    from src.data.pubchem_api import (
        build_panama_cid_list,
        enrich_corpus_with_smiles,
        fetch_ghs_labels,
    )

    print("=== Paso 1: CIDs (MIDA + clasificación HID 72) ===")
    df = build_panama_cid_list(str(cids_csv))

    print("\n=== Paso 2: SMILES canónicos (PubChem Compound + RDKit) ===")
    df = enrich_corpus_with_smiles(str(cids_csv))

    if not skip_ghs:
        print("\n=== Paso 3: Etiquetas GHS (validación externa) ===")
        fetch_ghs_labels([int(x) for x in df["CID"].tolist()], str(ghs_csv))
    else:
        print("\n=== Paso 3: Etiquetas GHS — omitido (--skip-ghs) ===")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construir corpus de plaguicidas panameños desde PubChem",
    )
    parser.add_argument(
        "--skip-pubchem",
        action="store_true",
        help="No llamar a PubChem; usar CSV existente en data/raw/",
    )
    parser.add_argument(
        "--skip-ghs",
        action="store_true",
        help="Omitir descarga de etiquetas GHS (más rápido)",
    )
    parser.add_argument(
        "--skip-graphs",
        action="store_true",
        help="Solo generar CSVs raw; no crear panama_corpus.pt",
    )
    parser.add_argument(
        "--cids-csv",
        type=Path,
        default=DEFAULT_CIDS_CSV,
        help=f"Ruta del CSV de CIDs/SMILES (default: {DEFAULT_CIDS_CSV})",
    )
    parser.add_argument(
        "--ghs-csv",
        type=Path,
        default=DEFAULT_GHS_CSV,
        help=f"Ruta del CSV de etiquetas GHS (default: {DEFAULT_GHS_CSV})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_GRAPHS_PT,
        help=f"Ruta del .pt con grafos PyG (default: {DEFAULT_GRAPHS_PT})",
    )
    args = parser.parse_args()

    if args.skip_pubchem:
        import pandas as pd

        if not args.cids_csv.is_file():
            print(f"ERROR: no existe {args.cids_csv}")
            print("Ejecuta sin --skip-pubchem para descargar desde PubChem.")
            sys.exit(1)
        print(f"Usando CSV existente: {args.cids_csv}")
        df = pd.read_csv(args.cids_csv)
    else:
        print("Descargando corpus desde PubChem (puede tardar varios minutos)…\n")
        df = run_pubchem_pipeline(
            args.cids_csv,
            args.ghs_csv,
            skip_ghs=args.skip_ghs,
        )

    corpus = None
    if not args.skip_graphs:
        print("\n=== Paso 4: Grafos moleculares (featurizer) ===")
        corpus = build_graphs_corpus(args.cids_csv, args.output)
        print(f"Guardado: {args.output} ({corpus['meta']['n_graphs']} grafos)")

    print_summary(df, corpus)

    if corpus is not None and corpus["meta"]["n_graphs"] < 30:
        print(
            "\nAVISO: menos de 30 grafos en panama_corpus.pt. "
            "Revisa la conexión a PubChem o el CSV de entrada."
        )

    print("\nArchivos generados:")
    print(f"  {args.cids_csv}")
    if not args.skip_ghs and not args.skip_pubchem:
        print(f"  {args.ghs_csv}")
    elif args.ghs_csv.is_file():
        print(f"  {args.ghs_csv} (existente)")
    if corpus is not None:
        print(f"  {args.output}")
    print("\nListo.")


if __name__ == "__main__":
    main()
