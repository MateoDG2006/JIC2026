"""
Métricas de evaluación multitarea y cross-validation con scaffold split.

Funciones principales:
  - evaluate_multitask_auc(): calcula AUC-ROC por tarea y promedio
  - evaluate_multitask_auprc(): calcula AUC-PR por tarea y promedio
  - create_scaffold_folds(): genera K folds agrupados por scaffold
"""

from __future__ import annotations

import random
from collections import defaultdict

import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.metrics import average_precision_score, roc_auc_score


def evaluate_multitask_auc(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mask: np.ndarray,
    task_names: list[str] | None = None,
) -> tuple[dict[str, float], float]:
    """Calcula AUC-ROC por tarea, ignorando posiciones sin medición.

    Solo calcula AUC para tareas que tienen al menos 1 ejemplo
    positivo y 1 negativo en las posiciones con medición.

    Args:
        y_true: (N, 12) — etiquetas reales (0 o 1)
        y_pred: (N, 12) — probabilidades predichas [0, 1]
        mask: (N, 12) — True donde hay medición
        task_names: nombres de las 12 tareas

    Returns:
        Tupla (dict_auc_por_tarea, auc_promedio)
    """
    n_tasks = y_true.shape[1]
    auc_per_task: dict[str, float] = {}
    for t in range(n_tasks):
        valid = mask[:, t].astype(bool)
        if valid.sum() == 0:
            continue
        y_t = y_true[valid, t]
        pred_t = y_pred[valid, t]
        # AUC requiere al menos 1 positivo y 1 negativo
        if len(np.unique(y_t)) < 2:
            continue
        name = task_names[t] if task_names else f"task_{t}"
        auc_per_task[name] = float(roc_auc_score(y_t, pred_t))
    if not auc_per_task:
        return {}, float("nan")
    mean_auc = float(np.mean(list(auc_per_task.values())))
    return auc_per_task, mean_auc


def evaluate_multitask_auprc(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mask: np.ndarray,
    task_names: list[str] | None = None,
) -> tuple[dict[str, float], float]:
    """Calcula AUC-PR (Average Precision) por tarea.

    AUC-PR es más informativo que AUC-ROC cuando hay mucho desbalance
    de clases (como en Tox21, donde algunas tareas tienen <5% positivos).
    """
    n_tasks = y_true.shape[1]
    ap_per_task: dict[str, float] = {}
    for t in range(n_tasks):
        valid = mask[:, t].astype(bool)
        if valid.sum() == 0:
            continue
        y_t = y_true[valid, t]
        pred_t = y_pred[valid, t]
        if len(np.unique(y_t)) < 2:
            continue
        name = task_names[t] if task_names else f"task_{t}"
        ap_per_task[name] = float(average_precision_score(y_t, pred_t))
    if not ap_per_task:
        return {}, float("nan")
    mean_ap = float(np.mean(list(ap_per_task.values())))
    return ap_per_task, mean_ap


# ── Cross-validation con scaffold split ──────────────────────────────────

def _murcko_scaffold(smiles: str, idx: int = -1) -> str:
    """Extrae el scaffold de Murcko de un SMILES.
    Para SMILES inválidos, retorna un scaffold único ficticio."""
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
    """Genera K folds agrupados por scaffold de Murcko.

    Garantiza que ningún scaffold aparezca en train Y val del mismo fold.
    Usa round-robin sobre scaffolds barajados para distribuir uniformemente.

    Args:
        smiles_list: lista completa de SMILES del dataset
        train_val_idx: índices a repartir (excluye test)
        n_folds: número de folds (default 5)
        seed: semilla para reproducibilidad

    Returns:
        Lista de (train_idx, val_idx) por fold
    """
    if n_folds < 2:
        raise ValueError("n_folds debe ser >= 2")
    idx_sorted = sorted(train_val_idx)
    if not idx_sorted:
        return []

    # Agrupar índices por scaffold
    groups: dict[str, list[int]] = defaultdict(list)
    for gi in idx_sorted:
        if gi < 0 or gi >= len(smiles_list):
            continue
        groups[_murcko_scaffold(smiles_list[gi], gi)].append(gi)

    # Barajar scaffolds y distribuir por round-robin
    scaffold_keys = list(groups.keys())
    rng = random.Random(seed)
    rng.shuffle(scaffold_keys)

    bins: list[list[str]] = [[] for _ in range(n_folds)]
    for i, key in enumerate(scaffold_keys):
        bins[i % n_folds].append(key)

    # Generar train/val para cada fold
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
