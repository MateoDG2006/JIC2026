"""Pérdida multitarea con máscara NaN — AGENTS.md, docs/04_entrenamiento.md."""

from __future__ import annotations

import torch
import torch.nn as nn


class MaskedBCELoss(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss(reduction="none")

    def forward(self, logits: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        loss_per = self.bce(logits, targets)
        m = mask.to(dtype=logits.dtype)
        denom = m.sum()
        if denom.item() == 0:
            return logits.sum() * 0.0
        return (loss_per * m).sum() / denom
