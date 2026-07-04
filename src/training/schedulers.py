"""LR schedulers para entrenamiento GIN.

Dos modos soportados:
  - ``cosine``: warmup lineal (10 épocas) → cosine annealing hasta eta_min
                Recomendado tras la auditoría (P1) — converge más suave.
  - ``plateau``: ReduceLROnPlateau que reduce el LR si val_auc no mejora
                  durante ``patience`` épocas.

La elección se hace en ``config.yaml`` → ``scheduler.type``.
"""

from __future__ import annotations

from typing import Any

import torch


def build_lr_scheduler(
    optimizer: torch.optim.Optimizer,
    config: dict[str, Any],
) -> tuple[Any, str]:
    """Construye el scheduler de LR a partir del ``config.yaml``.

    Args:
        optimizer: optimizador Adam del modelo GIN.
        config: dict de config (necesita ``scheduler`` y ``training.max_epochs``).

    Returns:
        Tupla ``(scheduler, mode)`` donde mode es:
          - ``"metric"`` → llamar ``scheduler.step(val_auc)`` cada época
          - ``"epoch"``  → llamar ``scheduler.step()`` cada época (sin métrica)
    """
    sched_cfg = config.get("scheduler", {})
    sched_type = sched_cfg.get("type", "plateau")
    max_epochs = int(config["training"]["max_epochs"])

    if sched_type == "cosine":
        warmup_epochs = int(sched_cfg.get("warmup_epochs", 10))
        warmup_epochs = max(1, min(warmup_epochs, max_epochs - 1))
        warmup = torch.optim.lr_scheduler.LinearLR(
            optimizer,
            start_factor=float(sched_cfg.get("warmup_start_factor", 0.1)),
            total_iters=warmup_epochs,
        )
        cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=max_epochs - warmup_epochs,
            eta_min=float(sched_cfg.get("eta_min", 1e-6)),
        )
        scheduler = torch.optim.lr_scheduler.SequentialLR(
            optimizer,
            schedulers=[warmup, cosine],
            milestones=[warmup_epochs],
        )
        return scheduler, "epoch"

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=float(sched_cfg.get("factor", 0.5)),
        patience=int(sched_cfg.get("patience", 15)),
    )
    return scheduler, "metric"
