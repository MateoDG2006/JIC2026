"""Métricas de entrenamiento — docs/04_entrenamiento.md."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score


def multitask_auc_dict(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mask: np.ndarray,
    task_names: list[str] | None = None,
) -> tuple[dict[str, float], float]:
    """Alias útil para evaluación; ver `evaluate_multitask_auc` en cross_validation."""
    from src.evaluation.cross_validation import evaluate_multitask_auc

    return evaluate_multitask_auc(y_true, y_pred, mask, task_names)
