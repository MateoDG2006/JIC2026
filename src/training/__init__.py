"""Entrenamiento de la GNN-GIN: trainer, pérdida enmascarada y schedulers.

Exporta:
    - MaskedBCELoss: BCE que ignora etiquetas NaN (Tox21 tiene mediciones faltantes)
    - train, train_epoch, evaluate: loop completo con early stopping
    - evaluate_multitask_auc/auprc: métricas re-exportadas para conveniencia

Submódulos:
    trainer      — loop principal, evaluación, gestión de checkpoints
    loss         — BCEWithLogitsLoss enmascarada para Tox21
    schedulers   — Cosine+warmup o ReduceLROnPlateau configurables
    checkpoint   — criterios para decidir cuándo guardar el mejor modelo
    metrics      — atajos a métricas de cross_validation
"""

from src.training.loss import MaskedBCELoss
from src.training.metrics import evaluate_multitask_auc, evaluate_multitask_auprc
from src.training.trainer import evaluate, train, train_epoch

__all__ = [
    "MaskedBCELoss",
    "evaluate_multitask_auc",
    "evaluate_multitask_auprc",
    "train",
    "train_epoch",
    "evaluate",
]
