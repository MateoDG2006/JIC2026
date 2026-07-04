"""Tests para MaskedBCELoss — la función de pérdida con máscara NaN."""

import torch

from src.training.loss import MaskedBCELoss


def test_masked_bce_all_masked_returns_zero():
    """Si todas las posiciones están enmascaradas (sin medición),
    la pérdida debe ser 0 sin romper el grafo de gradientes."""
    loss_fn = MaskedBCELoss()
    logits = torch.randn(4, 12)
    targets = torch.zeros(4, 12)
    mask = torch.zeros(4, 12, dtype=torch.bool)
    out = loss_fn(logits, targets, mask)
    assert out.item() == 0.0


def test_masked_bce_finite():
    """Con todas las posiciones medidas, la pérdida debe ser finita."""
    loss_fn = MaskedBCELoss()
    logits = torch.zeros(2, 12)
    targets = torch.zeros(2, 12)
    mask = torch.ones(2, 12, dtype=torch.bool)
    out = loss_fn(logits, targets, mask)
    assert torch.isfinite(out)


def test_masked_bce_with_pos_weight():
    """Verificar que pos_weight no causa errores con la máscara."""
    pw = torch.ones(12) * 5.0
    loss_fn = MaskedBCELoss(pos_weight=pw)
    logits = torch.randn(3, 12)
    targets = torch.ones(3, 12)
    mask = torch.ones(3, 12, dtype=torch.bool)
    out = loss_fn(logits, targets, mask)
    assert torch.isfinite(out)
