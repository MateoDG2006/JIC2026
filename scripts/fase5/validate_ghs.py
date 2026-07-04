#!/usr/bin/env python3
"""
Validación externa: predicciones del modelo vs etiquetas GHS de PubChem.

Uso:
  python scripts/fase5/validate_ghs.py \\
      --predictions outputs/results/panama_predictions.csv \\
      --ghs data/raw/pubchem_ghs_labels.csv \\
      --output outputs/reports/ghs_validation.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.dataset import TASK_NAMES  # noqa: E402


# Pares (columna predicción compuesta, columna GHS binaria, etiqueta legible)
GHS_PAIRS: list[tuple[str, str, str]] = [
    ("pred_endocrine", "endocrine_risk", "Endocrino (NR-AR/ER) vs H360/H361"),
    ("pred_genotox", "genotoxic", "Genotóxico (SR-p53/AtAD5) vs H340/H350"),
    ("pred_oxidative", "toxic_oral", "SR-ARE vs H300-H302"),
    ("pred_aquatic", "aquatic_tox", "Toxicidad acuática vs H400-H412"),
]


def add_composite_predictions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pred_endocrine"] = out[["NR-AR", "NR-ER", "NR-ER-LBD"]].max(axis=1)
    out["pred_genotox"] = out[["SR-p53", "SR-AtAD5"]].max(axis=1)
    out["pred_oxidative"] = out["SR-ARE"]
    out["pred_aquatic"] = out[TASK_NAMES].max(axis=1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Correlacionar predicciones panameñas con etiquetas GHS",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=ROOT / "outputs" / "results" / "panama_predictions.csv",
    )
    parser.add_argument(
        "--ghs",
        type=Path,
        default=ROOT / "data" / "raw" / "pubchem_ghs_labels.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "reports" / "ghs_validation.csv",
    )
    args = parser.parse_args()

    if not args.predictions.is_file():
        print(f"ERROR: no existe {args.predictions}")
        print("Ejecuta: make explain-panama")
        sys.exit(1)
    if not args.ghs.is_file():
        print(f"ERROR: no existe {args.ghs}")
        print("Ejecuta: make build-panama-corpus")
        sys.exit(1)

    pred_df = pd.read_csv(args.predictions)
    ghs_df = pd.read_csv(args.ghs)
    pred_df = add_composite_predictions(pred_df)

    merged = pred_df.merge(
        ghs_df,
        left_on="cid",
        right_on="CID",
        how="left",
    )

    print("Correlación Spearman (predicción continua vs etiqueta GHS binaria):\n")
    summary_rows: list[dict] = []
    for pred_col, ghs_col, label in GHS_PAIRS:
        sub = merged[[pred_col, ghs_col]].dropna()
        if sub.empty or sub[ghs_col].nunique() < 2:
            rho = None
            n = len(sub)
            note = "sin variación en GHS"
            print(f"  {label}: {note} (n={n})")
        else:
            rho = float(sub[pred_col].corr(sub[ghs_col], method="spearman"))
            n = len(sub)
            note = ""
            print(f"  {label}: ρ = {rho:.3f} (n={n})")
        summary_rows.append({
            "comparison": label,
            "pred_column": pred_col,
            "ghs_column": ghs_col,
            "spearman_rho": rho,
            "n_compounds": n,
            "note": note,
        })

    out_cols = [
        "compuesto", "cid", "familia", "tarea_critica", "prob_max", "alerta",
        "pred_endocrine", "pred_genotox", "pred_oxidative",
        "ghs_codes", "toxic_oral", "endocrine_risk", "genotoxic", "aquatic_tox",
    ]
    out_cols = [c for c in out_cols if c in merged.columns]
    detail = merged[out_cols].copy()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    detail.to_csv(args.output, index=False)

    summary_path = args.output.with_name("ghs_validation_summary.csv")
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)

    print(f"\nDetalle por compuesto: {args.output}")
    print(f"Resumen correlaciones: {summary_path}")
    print("Listo.")


if __name__ == "__main__":
    main()
