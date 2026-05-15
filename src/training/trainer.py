"""Loop de entrenamiento — docs/04_entrenamiento.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch_geometric.loader import DataLoader

from src.evaluation.cross_validation import evaluate_multitask_auc
from src.training.loss import MaskedBCELoss


def train_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: MaskedBCELoss,
    device: torch.device,
    grad_clip: float = 1.0,
) -> float:
    model.train()
    total = 0.0
    for batch in loader:
        batch = batch.to(device)
        logits = model(batch.x, batch.edge_index, batch.batch)
        loss = loss_fn(logits, batch.y, batch.mask)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
        optimizer.step()
        total += float(loss.detach())
    return total / max(len(loader), 1)


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    task_names: list[str] | None = None,
) -> tuple[dict[str, float], float]:
    model.eval()
    all_logits: list[torch.Tensor] = []
    all_y: list[torch.Tensor] = []
    all_m: list[torch.Tensor] = []
    for batch in loader:
        batch = batch.to(device)
        logits = model(batch.x, batch.edge_index, batch.batch)
        all_logits.append(logits.cpu())
        all_y.append(batch.y.cpu())
        all_m.append(batch.mask.cpu())
    preds = torch.sigmoid(torch.cat(all_logits, dim=0)).numpy()
    labels = torch.cat(all_y, dim=0).numpy()
    masks = torch.cat(all_m, dim=0).numpy()
    return evaluate_multitask_auc(labels, preds, masks, task_names)


def train(
    model: torch.nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: dict[str, Any],
    device: torch.device,
    task_names: list[str] | None = None,
    use_wandb: bool = False,
) -> float:
    opt = torch.optim.Adam(model.parameters(), lr=float(config["training"]["lr"]))
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt,
        mode="max",
        factor=float(config["scheduler"]["factor"]),
        patience=int(config["scheduler"]["patience"]),
    )
    loss_fn = MaskedBCELoss()
    save_path = Path(config["training"]["model_save_path"])
    save_path.parent.mkdir(parents=True, exist_ok=True)

    best = 0.0
    bad = 0
    patience = int(config["training"]["early_stopping_patience"])
    max_epochs = int(config["training"]["max_epochs"])

    if use_wandb:
        import wandb

    for epoch in range(max_epochs):
        tl = train_epoch(
            model,
            train_loader,
            opt,
            loss_fn,
            device,
            grad_clip=float(config["training"]["grad_clip_norm"]),
        )
        _, val_auc = evaluate(model, val_loader, device, task_names)
        if not np.isfinite(val_auc):
            if use_wandb:
                wandb.log(
                    {
                        "epoch": epoch,
                        "train_loss": tl,
                        "val_auc": float("nan"),
                        "lr": opt.param_groups[0]["lr"],
                    }
                )
            bad += 1
            if bad >= patience:
                break
            continue

        sched.step(val_auc)
        if use_wandb:
            wandb.log(
                {
                    "epoch": epoch,
                    "train_loss": tl,
                    "val_auc": val_auc,
                    "lr": opt.param_groups[0]["lr"],
                }
            )
        if val_auc > best:
            best = val_auc
            bad = 0
            torch.save(model.state_dict(), save_path)
        else:
            bad += 1
            if bad >= patience:
                break
    return best
