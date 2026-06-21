"""Evaluación de modelos: métricas multitarea, scaffold folds y validación XAI.

Exporta:
    - evaluate_multitask_auc/auprc: AUC y AUPRC por tarea Tox21 con máscara NaN
    - create_scaffold_folds: K-folds agrupados por scaffold de Murcko
    - TOXIC_GROUPS: diccionario SMARTS de grupos funcionales tóxicos por vía
    - precision_at_k: métrica de coherencia química para explicaciones XAI
"""

from src.evaluation.chemical_coherence import TOXIC_GROUPS, precision_at_k
from src.evaluation.cross_validation import (
    create_scaffold_folds,
    evaluate_multitask_auc,
    evaluate_multitask_auprc,
)

__all__ = [
    "evaluate_multitask_auc",
    "evaluate_multitask_auprc",
    "create_scaffold_folds",
    "TOXIC_GROUPS",
    "precision_at_k",
]
