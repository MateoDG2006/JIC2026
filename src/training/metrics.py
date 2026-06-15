"""
Funciones de métricas para evaluación de modelos.

Re-exporta evaluate_multitask_auc y evaluate_multitask_auprc
desde cross_validation para conveniencia de importación.
"""

from __future__ import annotations

from src.evaluation.cross_validation import (
    evaluate_multitask_auc,
    evaluate_multitask_auprc,
)

# Re-exportar para que se pueda usar:
#   from src.training.metrics import evaluate_multitask_auc
__all__ = ["evaluate_multitask_auc", "evaluate_multitask_auprc"]
