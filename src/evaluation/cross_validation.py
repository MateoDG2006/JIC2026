"""AUC multitarea y utilidades de CV — docs/04_entrenamiento.md."""

from __future__ import annotations

import random
from collections import defaultdict

import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.metrics import roc_auc_score


def evaluate_multitask_auc(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mask: np.ndarray,
    task_names: list[str] | None = None,
) -> tuple[dict[str, float], float]:
    n_tasks = y_true.shape[1]
    auc_per_task: dict[str, float] = {}
    for t in range(n_tasks):
        valid = mask[:, t].astype(bool)
        if valid.sum() == 0:
            continue
        y_t = y_true[valid, t]
        pred_t = y_pred[valid, t]
        if len(np.unique(y_t)) < 2:
            continue
        name = task_names[t] if task_names else f"task_{t}"
        auc_per_task[name] = float(roc_auc_score(y_t, pred_t))
    if not auc_per_task:
        return {}, float("nan")
    mean_auc = float(np.mean(list(auc_per_task.values())))
    return auc_per_task, mean_auc


def _murcko_scaffold(smiles: str, idx: int = -1) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return f"__invalid__::{idx}"
    return MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)


def create_scaffold_folds(
    smiles_list: list[str],
    train_val_idx: list[int],
    n_folds: int = 5,
    seed: int = 42,
) -> list[tuple[list[int], list[int]]]:
    """K-fold agrupando por scaffold Murcko (ML-2): ningún scaffold aparece en train y val a la vez.

    Reparte **grupos** de scaffold en `n_folds` bins por round-robin (tras barajar, `seed`).
    El conjunto de test debe fijarse fuera y no incluirse en `train_val_idx` (AGENTS.md).
    """
    if n_folds < 2:
        raise ValueError("n_folds debe ser >= 2")
    idx_sorted = sorted(train_val_idx)
    if not idx_sorted:
        return []

    groups: dict[str, list[int]] = defaultdict(list)
    for gi in idx_sorted:
        if gi < 0 or gi >= len(smiles_list):
            continue
        groups[_murcko_scaffold(smiles_list[gi], gi)].append(gi)

    scaffold_keys = list(groups.keys())
    rng = random.Random(seed)
    rng.shuffle(scaffold_keys)

    bins: list[list[str]] = [[] for _ in range(n_folds)]
    for i, key in enumerate(scaffold_keys):
        bins[i % n_folds].append(key)

    folds: list[tuple[list[int], list[int]]] = []
    for k in range(n_folds):
        val_scaffold_set = set(bins[k])
        val_idx: list[int] = []
        for sc in val_scaffold_set:
            val_idx.extend(groups[sc])
        val_set = set(val_idx)
        train_idx = [gi for gi in idx_sorted if gi not in val_set]
        folds.append((train_idx, sorted(val_idx)))
    return folds
