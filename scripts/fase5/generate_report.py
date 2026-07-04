#!/usr/bin/env python3
"""
Genera reporte interpretado para MIDA/MINSA a partir de predicciones y XAI.

Salidas:
  outputs/reports/report_mida_minsa.md
  outputs/reports/report_mida_minsa.pdf  (resumen visual)

Uso:
  python scripts/fase5/generate_report.py --results outputs/xai/ --output outputs/reports/
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.dataset import TASK_NAMES  # noqa: E402
from src.data.pubchem_api import MIDA_ACTIVE_INGREDIENTS  # noqa: E402

PRIORITY_COMPOUNDS = [
    "Chlorpyrifos", "Atrazine", "Tebuconazole",
    "Cypermethrin", "Paraquat", "Glyphosate",
]


def slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "compound"

TASK_DESCRIPTIONS: dict[str, str] = {
    "NR-AR": "Receptor de andrógenos",
    "NR-AR-LBD": "Dominio ligando AR",
    "NR-AhR": "Receptor aril-hidrocarburo",
    "NR-Aromatase": "Aromatasa (CYP19)",
    "NR-ER": "Receptor de estrógenos",
    "NR-ER-LBD": "Dominio ligando ER",
    "NR-PPAR-gamma": "Receptor PPAR-γ",
    "SR-ARE": "Estrés oxidativo (Nrf2)",
    "SR-AtAD5": "Daño al ADN",
    "SR-HSE": "Estrés por calor",
    "SR-MMP": "Membrana mitocondrial",
    "SR-p53": "Vía p53 (genotoxicidad)",
}


def load_profile() -> pd.DataFrame:
    path = ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv"
    if not path.is_file():
        alt = ROOT / "outputs" / "results" / "panama_predictions.csv"
        if not alt.is_file():
            raise FileNotFoundError(
                "No hay predicciones. Ejecuta: make explain-panama"
            )
        return pd.read_csv(alt)
    return pd.read_csv(path)


def write_markdown(df: pd.DataFrame, xai_dir: Path, out_path: Path) -> None:
    mida_lower = {n.lower() for n in MIDA_ACTIVE_INGREDIENTS}
    mida_df = df[df["compuesto"].str.lower().isin(mida_lower)].sort_values(
        "prob_max", ascending=False
    )
    prio = df[df["compuesto"].isin(PRIORITY_COMPOUNDS)]
    if prio.empty:
        prio = mida_df.head(6)

    lines: list[str] = [
        "# Perfil de toxicidad computacional — Plaguicidas de Panamá",
        "",
        f"**Fecha:** {date.today().isoformat()}  ",
        "**Modelo:** GNN-GIN entrenada sobre Tox21 (12 dianas biológicas)  ",
        f"**Compuestos evaluados:** {len(df)}  ",
        f"**Ingredientes activos MIDA:** {len(mida_df)} / {len(MIDA_ACTIVE_INGREDIENTS)}",
        "",
        "## Resumen ejecutivo",
        "",
        "Este reporte resume predicciones de toxicidad multitarea y explicaciones",
        "XAI (átomos clave) para plaguicidas del corpus panameño. Los niveles de",
        "riesgo se basan en la probabilidad máxima entre las 12 vías Tox21:",
        "",
        "- **ALTO**: P > 0.7",
        "- **MODERADO**: 0.4 < P ≤ 0.7",
        "- **BAJO**: P ≤ 0.4",
        "",
    ]

    if "alerta" in df.columns:
        counts = df["alerta"].value_counts()
        lines.append("### Distribución de alertas (corpus completo)")
        lines.append("")
        for level, n in counts.items():
            lines.append(f"- {level}: {n}")
        lines.append("")

    lines += ["## Casos prioritarios", ""]
    for _, row in prio.iterrows():
        task = row["tarea_critica"]
        desc = TASK_DESCRIPTIONS.get(task, task)
        lines += [
            f"### {row['compuesto']}",
            "",
            f"- **Familia:** {row.get('familia', '—')}",
            f"- **CID PubChem:** {row.get('cid', '—')}",
            f"- **Vía crítica:** {task} — {desc}",
            f"- **Probabilidad máxima:** {row['prob_max']:.2f}",
            f"- **Nivel de alerta:** {row['alerta']}",
            "",
        ]
        fig_dir = xai_dir / "figures"
        slug = slugify(str(row["compuesto"]))
        for method in ("gnnexplainer", "gradcam"):
            fig = fig_dir / f"{slug}_{task}_{method}.svg"
            if fig.is_file():
                lines.append(f"![XAI {method}]({fig.as_posix()})")
                lines.append("")
        lines.append("---")
        lines.append("")

    lines += [
        "## Metodología",
        "",
        "1. Corpus molecular desde PubChem (ingredientes MIDA + familias químicas).",
        "2. Conversión SMILES → grafo molecular (RDKit + PyTorch Geometric).",
        "3. Predicción multitarea con GNN-GIN.",
        "4. Explicación XAI: GNNExplainer y Grad-CAM sobre la vía de mayor riesgo.",
        "5. Validación externa opcional contra etiquetas GHS (no usadas en entrenamiento).",
        "",
        "*Generado automáticamente por scripts/fase5/generate_report.py*",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_pdf(df: pd.DataFrame, out_path: Path) -> None:
    mida_lower = {n.lower() for n in MIDA_ACTIVE_INGREDIENTS}
    mida_df = df[df["compuesto"].str.lower().isin(mida_lower)].sort_values(
        "prob_max", ascending=False
    )
    plot_df = mida_df if len(mida_df) >= 6 else df.nlargest(15, "prob_max")

    colors = {"ALTO": "#d62728", "MODERADO": "#ff7f0e", "BAJO": "#2ca02c"}

    with PdfPages(out_path) as pdf:
        # Página 1: barras casos prioritarios
        prio = df[df["compuesto"].isin(PRIORITY_COMPOUNDS)]
        if prio.empty:
            prio = plot_df.head(8)

        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")
        ax.text(
            0.5, 0.95,
            "Perfil de toxicidad — Plaguicidas de Panamá",
            ha="center", va="top", fontsize=16, fontweight="bold",
            transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.90,
            f"Fecha: {date.today().isoformat()} | Compuestos: {len(df)}",
            ha="center", va="top", fontsize=10, transform=ax.transAxes,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8.5, max(4, 0.45 * len(prio))))
        bar_colors = [colors.get(a, "gray") for a in prio["alerta"]]
        ax.barh(prio["compuesto"], prio["prob_max"], color=bar_colors)
        ax.axvline(0.7, color="red", ls="--", alpha=0.5, label="ALTO (0.7)")
        ax.axvline(0.4, color="orange", ls="--", alpha=0.5, label="MODERADO (0.4)")
        ax.set_xlabel("Probabilidad máxima de toxicidad")
        ax.set_title("Casos prioritarios")
        ax.legend(loc="lower right")
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Página 2: mapa de calor MIDA
        if len(plot_df) > 0:
            heat = plot_df.set_index("compuesto")[TASK_NAMES]
            fig_h = max(5, 0.35 * len(heat))
            fig, ax = plt.subplots(figsize=(11, fig_h))
            im = ax.imshow(heat.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
            ax.set_xticks(range(len(TASK_NAMES)))
            ax.set_xticklabels(TASK_NAMES, rotation=45, ha="right")
            ax.set_yticks(range(len(heat)))
            ax.set_yticklabels(heat.index)
            ax.set_title("Perfil multitarea Tox21")
            plt.colorbar(im, ax=ax, fraction=0.02)
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generar reporte MIDA/MINSA")
    parser.add_argument(
        "--results",
        type=Path,
        default=ROOT / "outputs" / "xai",
        help="Directorio con figures/ y explanations/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "reports",
    )
    args = parser.parse_args()

    df = load_profile()
    args.output.mkdir(parents=True, exist_ok=True)

    md_path = args.output / "report_mida_minsa.md"
    pdf_path = args.output / "report_mida_minsa.pdf"

    write_markdown(df, args.results, md_path)
    write_pdf(df, pdf_path)

    print(f"Reporte Markdown: {md_path}")
    print(f"Reporte PDF:      {pdf_path}")
    print("Listo.")


if __name__ == "__main__":
    main()
