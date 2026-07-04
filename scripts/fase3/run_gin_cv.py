#!/usr/bin/env python
"""
5-fold cross-validation scaffold para GNN-GIN (AUDIT E2 / P1).

Uso:
  python scripts/fase3/run_gin_cv.py --config config/config.yaml
  python scripts/fase3/run_gin_cv.py --folds 5 --max-epochs 50   # prueba rápida
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fase1.prepare_tox21_graphs import _build_list, _extract_smiles_y_mask  # noqa: E402
from scripts.fase3.train_gin import (  # noqa: E402
    compute_pos_weight,
    load_config,
    resolve_device,
    set_seed,
)
from src.data.dataset import TASK_NAMES
from src.data.tox21_deepchem import load_tox21_raw_scaffold
from src.evaluation.cross_validation import create_scaffold_folds
from src.models.gin import GINToxicity
from src.training.trainer import evaluate, train


class _GraphListDS:
    """Wrapper mínimo para reutilizar compute_pos_weight sobre listas de grafos."""

    def __init__(self, graphs: list[Data]) -> None:
        self.graphs = graphs

    def __len__(self) -> int:
        return len(self.graphs)

    def __iter__(self):
        return iter(self.graphs)

    def __getitem__(self, idx: int) -> Data:
        return self.graphs[idx]


def _load_train_val_graphs() -> tuple[list[Data], list[str]]:
    _tasks, splits, _ = load_tox21_raw_scaffold()
    train_ds, val_ds, _ = splits
    smiles: list[str] = []
    ys: list[np.ndarray] = []
    ms: list[np.ndarray] = []
    for ds in (train_ds, val_ds):
        smi, y, m = _extract_smiles_y_mask(ds)
        smiles.extend(smi)
        ys.append(y)
        ms.append(m)
    y_all = np.vstack(ys)
    m_all = np.vstack(ms)
    graphs = _build_list(smiles, y_all, m_all)
    return graphs, smiles


def main() -> int:
    parser = argparse.ArgumentParser(description="5-fold CV GIN-GIN scaffold")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "config.yaml")
    parser.add_argument("--folds", type=int, default=None, help="Override evaluation.n_folds")
    parser.add_argument("--max-epochs", type=int, default=None, help="Override para prueba rápida")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = load_config(args.config)
    n_folds = args.folds or int(cfg["evaluation"]["n_folds"])
    if args.max_epochs:
        cfg["training"]["max_epochs"] = args.max_epochs

    device = resolve_device(args.device, require_gpu=False)
    set_seed(args.seed, device)

    print("Cargando train+val Tox21 para CV...")
    graphs, smiles = _load_train_val_graphs()
    indices = list(range(len(graphs)))
    folds = create_scaffold_folds(smiles, indices, n_folds=n_folds, seed=args.seed)
    print(f"  {len(graphs)} grafos | {n_folds} folds scaffold")

    results: list[dict] = []
    batch_size = int(cfg["training"]["batch_size"])

    for fold_i, (train_idx, val_idx) in enumerate(folds, start=1):
        print(f"\n=== Fold {fold_i}/{n_folds} ===")
        train_data = [graphs[i] for i in train_idx]
        val_data = [graphs[i] for i in val_idx]
        train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False)

        pos_weight = compute_pos_weight(_GraphListDS(train_data))

        model = GINToxicity(
            node_feat_dim=int(cfg["model"]["node_feat_dim"]),
            edge_feat_dim=int(cfg["model"]["edge_feat_dim"]),
            hidden_dim=int(cfg["model"]["hidden_dim"]),
            n_layers=int(cfg["model"]["n_layers"]),
            n_tasks=int(cfg["model"]["n_tasks"]),
            dropout=float(cfg["model"]["dropout"]),
        ).to(device)

        fold_cfg = dict(cfg)
        fold_cfg["training"] = dict(cfg["training"])
        fold_cfg["training"]["model_save_path"] = str(
            ROOT / "outputs" / "models" / f"gin_fold_{fold_i}.pt"
        )

        best_val = train(
            model, train_loader, val_loader, fold_cfg, device,
            task_names=TASK_NAMES, pos_weight=pos_weight,
        )
        auc_val, mean_val = evaluate(model, val_loader, device, TASK_NAMES)
        row: dict = {"fold": fold_i, "mean_auc": mean_val, "best_val_auc": best_val}
        row.update(auc_val)
        results.append(row)
        print(f"  Fold {fold_i} val AUC: {mean_val:.4f}")

    df = pd.DataFrame(results)
    out = ROOT / "outputs" / "results" / "gin_cv_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    mean_col = df["mean_auc"].mean()
    std_col = df["mean_auc"].std()
    print(f"\nCV completada: {mean_col:.4f} ± {std_col:.4f}")
    print(f"Guardado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
