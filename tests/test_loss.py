import torch

from src.training.loss import MaskedBCELoss


def test_masked_bce_all_masked_returns_zero():
    loss_fn = MaskedBCELoss()
    logits = torch.randn(4, 12)
    targets = torch.zeros(4, 12)
    mask = torch.zeros(4, 12, dtype=torch.bool)
    out = loss_fn(logits, targets, mask)
    assert out.item() == 0.0


def test_masked_bce_finite():
    loss_fn = MaskedBCELoss()
    logits = torch.zeros(2, 12)
    targets = torch.zeros(2, 12)
    mask = torch.ones(2, 12, dtype=torch.bool)
    out = loss_fn(logits, targets, mask)
    assert torch.isfinite(out)
