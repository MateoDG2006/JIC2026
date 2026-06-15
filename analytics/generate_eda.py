"""
Análisis exploratorio de datos (EDA) para el dataset Tox21.

Genera gráficos de:
  1. Distribución de clases por tarea (% positivos vs negativos)
  2. Distribución de datos faltantes (NaN) por tarea
  3. Distribución de tamaño molecular (número de átomos)
  4. Matriz de correlación entre tareas
  5. Distribución de scaffolds

Los gráficos se guardan en outputs/eda/.

Uso:
  python analytics/generate_eda.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Nombres de las 12 tareas Tox21
TASK_NAMES = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-AtAD5", "SR-HSE", "SR-MMP", "SR-p53",
]


def load_tox21_data():
    """Carga Tox21 desde DeepChem y extrae SMILES, etiquetas y máscara."""
    import deepchem as dc
    from scripts.prepare_tox21_graphs import _extract_smiles_y_mask

    _, splits, _ = dc.molnet.load_tox21(
        featurizer=dc.feat.RawFeaturizer(),
        splitter="scaffold",
    )
    train_ds, val_ds, test_ds = splits

    all_smiles = []
    all_y = []
    all_mask = []
    split_labels = []

    for name, ds in [("train", train_ds), ("val", val_ds), ("test", test_ds)]:
        smi, y, m = _extract_smiles_y_mask(ds)
        all_smiles.extend(smi)
        all_y.append(y)
        all_mask.append(m)
        split_labels.extend([name] * len(smi))

    y = np.concatenate(all_y, axis=0)
    mask = np.concatenate(all_mask, axis=0)
    return all_smiles, y, mask, split_labels


def plot_class_distribution(y: np.ndarray, mask: np.ndarray, out_dir: Path) -> None:
    """Gráfico de barras: % positivos por tarea."""
    fig, ax = plt.subplots(figsize=(12, 5))
    pct_pos = []
    for t in range(12):
        valid = mask[:, t].astype(bool)
        if valid.sum() == 0:
            pct_pos.append(0)
        else:
            pct_pos.append(100 * y[valid, t].sum() / valid.sum())

    colors = ["#e74c3c" if p > 10 else "#f39c12" if p > 5 else "#3498db" for p in pct_pos]
    bars = ax.bar(range(12), pct_pos, color=colors, edgecolor="white")
    ax.set_xticks(range(12))
    ax.set_xticklabels(TASK_NAMES, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("% Positivos")
    ax.set_title("Distribución de Clases por Tarea Tox21")
    ax.axhline(y=5, color="gray", linestyle="--", alpha=0.5, label="5% (desbalance severo)")
    ax.legend()
    for bar, val in zip(bars, pct_pos):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{val:.1f}%", ha="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "01_class_distribution.png", dpi=150)
    plt.close()
    print(f"  Guardado: 01_class_distribution.png")


def plot_nan_distribution(mask: np.ndarray, out_dir: Path) -> None:
    """Gráfico de barras: % de datos faltantes por tarea."""
    fig, ax = plt.subplots(figsize=(12, 5))
    n_total = mask.shape[0]
    pct_missing = [100 * (1 - mask[:, t].mean()) for t in range(12)]

    ax.bar(range(12), pct_missing, color="#95a5a6", edgecolor="white")
    ax.set_xticks(range(12))
    ax.set_xticklabels(TASK_NAMES, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("% Datos Faltantes")
    ax.set_title(f"Datos Faltantes (NaN) por Tarea Tox21 (n={n_total})")
    plt.tight_layout()
    plt.savefig(out_dir / "02_nan_distribution.png", dpi=150)
    plt.close()
    print(f"  Guardado: 02_nan_distribution.png")


def plot_molecule_sizes(smiles_list: list[str], out_dir: Path) -> None:
    """Histograma de número de átomos por molécula."""
    from rdkit import Chem

    sizes = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            sizes.append(mol.GetNumAtoms())

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(sizes, bins=50, color="#2ecc71", edgecolor="white", alpha=0.8)
    ax.axvline(np.median(sizes), color="red", linestyle="--",
               label=f"Mediana: {np.median(sizes):.0f} átomos")
    ax.set_xlabel("Número de Átomos")
    ax.set_ylabel("Frecuencia")
    ax.set_title("Distribución de Tamaño Molecular en Tox21")
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "03_molecule_sizes.png", dpi=150)
    plt.close()
    print(f"  Guardado: 03_molecule_sizes.png")


def plot_task_correlation(y: np.ndarray, mask: np.ndarray, out_dir: Path) -> None:
    """Mapa de calor: correlación entre tareas (solo usando datos medidos)."""
    import pandas as pd

    y_masked = y.copy()
    y_masked[~mask.astype(bool)] = np.nan
    df = pd.DataFrame(y_masked, columns=TASK_NAMES)
    corr = df.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                xticklabels=TASK_NAMES, yticklabels=TASK_NAMES,
                ax=ax, vmin=-1, vmax=1)
    ax.set_title("Correlación entre Tareas Tox21")
    plt.tight_layout()
    plt.savefig(out_dir / "04_task_correlation.png", dpi=150)
    plt.close()
    print(f"  Guardado: 04_task_correlation.png")


def plot_split_sizes(split_labels: list[str], out_dir: Path) -> None:
    """Gráfico de torta: proporción train/val/test."""
    from collections import Counter
    counts = Counter(split_labels)
    labels = ["Train", "Val", "Test"]
    sizes = [counts.get("train", 0), counts.get("val", 0), counts.get("test", 0)]
    colors = ["#3498db", "#f39c12", "#e74c3c"]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(sizes, labels=[f"{l}\n({s})" for l, s in zip(labels, sizes)],
           colors=colors, autopct="%1.1f%%", startangle=90)
    ax.set_title("Distribución del Scaffold Split")
    plt.tight_layout()
    plt.savefig(out_dir / "05_split_sizes.png", dpi=150)
    plt.close()
    print(f"  Guardado: 05_split_sizes.png")


def main() -> None:
    out_dir = ROOT / "outputs" / "eda"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Cargando Tox21 desde DeepChem...")
    smiles, y, mask, split_labels = load_tox21_data()
    print(f"  Total: {len(smiles)} moléculas, {y.shape[1]} tareas")

    print("\nGenerando gráficos EDA...")
    plot_class_distribution(y, mask, out_dir)
    plot_nan_distribution(mask, out_dir)
    plot_molecule_sizes(smiles, out_dir)
    plot_task_correlation(y, mask, out_dir)
    plot_split_sizes(split_labels, out_dir)

    print(f"\nTodos los gráficos guardados en {out_dir}")


if __name__ == "__main__":
    main()
