"""
Función de pérdida con máscara para datos faltantes (NaN).

Tox21 tiene mediciones faltantes: no todas las moléculas fueron testeadas
en los 12 ensayos. Las posiciones sin medición se marcan con mask=0.

Esta pérdida solo calcula el error sobre las posiciones con medición real,
e incluye soporte para pos_weight (compensar desbalance de clases).
"""

from __future__ import annotations

import torch
import torch.nn as nn


class MaskedBCELoss(nn.Module):
    """
    BCEWithLogitsLoss enmascarada para tareas multitarea con datos faltantes.

    Args:
        pos_weight: tensor de pesos por tarea para compensar desbalance.
                    Si la tarea NR-AR tiene 5% positivos, su pos_weight
                    debería ser ~19 (95/5) para penalizar más los falsos negativos.
                    Si es None, todas las clases pesan igual.
    """

    def __init__(self, pos_weight: torch.Tensor | None = None) -> None:
        super().__init__()
        # reduction="none" para poder aplicar la máscara elemento por elemento
        self.bce = nn.BCEWithLogitsLoss(reduction="none", pos_weight=pos_weight)

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            logits: (batch_size, 12) — salidas del modelo SIN sigmoid
            targets: (batch_size, 12) — etiquetas 0.0 o 1.0
            mask: (batch_size, 12) — True donde hay medición, False donde hay NaN

        Returns:
            Pérdida escalar — promedio solo sobre las posiciones con medición
        """
        # Calcular pérdida por cada posición (batch × 12)
        loss_per = self.bce(logits, targets)

        # Convertir máscara a float para multiplicar (True→1.0, False→0.0)
        m = mask.to(dtype=logits.dtype)

        # Contar cuántas posiciones tienen medición
        denom = m.sum()

        # Si no hay ninguna medición en este batch, retornar 0 sin romper el grafo
        if denom.item() == 0:
            return logits.sum() * 0.0

        # Promediar solo sobre las posiciones con medición real
        return (loss_per * m).sum() / denom
