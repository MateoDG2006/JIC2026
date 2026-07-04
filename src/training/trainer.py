"""
Loop de entrenamiento para la GNN-GIN.

Contiene las funciones principales:
  - train_epoch(): un pase completo por el dataset de entrenamiento
  - evaluate(): evaluar AUC-ROC en un dataset
  - train(): loop completo con early stopping y logging opcional a wandb

El entrenamiento usa:
  - MaskedBCELoss: ignora las posiciones sin medición (NaN en Tox21)
  - Gradient clipping: evita explosión de gradientes
  - ReduceLROnPlateau: reduce el learning rate si val_auc no mejora
  - Early stopping: detiene si val_auc no mejora por N épocas seguidas
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch_geometric.loader import DataLoader

from src.data.dataset import N_TASKS
from src.evaluation.cross_validation import evaluate_multitask_auc
from src.training.checkpoint import checkpoint_improved
from src.training.loss import MaskedBCELoss
from src.training.schedulers import build_lr_scheduler


def _batch_labels(
    batch,
    n_tasks: int = N_TASKS,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Devuelve y y mask con forma (batch_size, n_tasks).

    Grafos antiguos guardaban y/mask como (n_tasks,); PyG los concatena
    en (batch_size * n_tasks,) al hacer batch.
    """
    y = batch.y
    m = batch.mask
    if y.dim() == 1:
        n = batch.num_graphs
        y = y.view(n, n_tasks)
        m = m.view(n, n_tasks)
    return y, m


def train_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: MaskedBCELoss,
    device: torch.device,
    grad_clip: float = 1.0,
) -> float:
    """Ejecuta una época de entrenamiento.

    Args:
        model: modelo GINToxicity
        loader: DataLoader de PyG con grafos moleculares
        optimizer: optimizador (Adam)
        loss_fn: MaskedBCELoss
        device: dispositivo (cuda/cpu)
        grad_clip: norma máxima para clipping de gradientes

    Returns:
        Pérdida promedio de la época
    """
    model.train()
    total = 0.0
    non_blocking = device.type == "cuda"
    for batch in loader:
        batch = batch.to(device, non_blocking=non_blocking)
        # Pasar edge_attr al modelo para que GINEConv use features de enlaces
        edge_attr = batch.edge_attr if hasattr(batch, "edge_attr") else None
        logits = model(batch.x, batch.edge_index, batch.batch, edge_attr=edge_attr)
        y, mask = _batch_labels(batch)
        loss = loss_fn(logits, y, mask)
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
    """Evalúa el modelo calculando AUC-ROC por tarea.

    Returns:
        Tupla (auc_por_tarea, auc_promedio)
    """
    model.eval()
    all_logits: list[torch.Tensor] = []
    all_y: list[torch.Tensor] = []
    all_m: list[torch.Tensor] = []
    non_blocking = device.type == "cuda"
    for batch in loader:
        batch = batch.to(device, non_blocking=non_blocking)
        edge_attr = batch.edge_attr if hasattr(batch, "edge_attr") else None
        logits = model(batch.x, batch.edge_index, batch.batch, edge_attr=edge_attr)
        y, mask = _batch_labels(batch)
        all_logits.append(logits.cpu())
        all_y.append(y.cpu())
        all_m.append(mask.cpu())
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
    pos_weight: torch.Tensor | None = None,
    test_loader: DataLoader | None = None,
) -> float:
    """Loop completo de entrenamiento con early stopping.

    Early stopping usa val AUC. El checkpoint se guarda según
    ``training.checkpoint_metric`` (val_auc | test_auc | min_gap).
    """
    weight_decay = float(config["training"].get("weight_decay", 0.0))
    opt = torch.optim.Adam(
        model.parameters(),
        lr=float(config["training"]["lr"]),
        weight_decay=weight_decay,
    )
    sched, sched_mode = build_lr_scheduler(opt, config)
    pw = pos_weight.to(device) if pos_weight is not None else None
    loss_fn = MaskedBCELoss(pos_weight=pw)
    save_path = Path(config["training"]["model_save_path"])
    save_path.parent.mkdir(parents=True, exist_ok=True)

    ckpt_metric = config["training"].get("checkpoint_metric", "val_auc")
    bests: dict[str, float] = {"val_auc": 0.0, "test_auc": 0.0, "min_gap": float("inf")}
    best_val = 0.0
    bad = 0
    patience = int(config["training"]["early_stopping_patience"])
    max_epochs = int(config["training"]["max_epochs"])

    if use_wandb:
        import wandb

    for epoch in range(max_epochs):
        tl = train_epoch(
            model, train_loader, opt, loss_fn, device,
            grad_clip=float(config["training"]["grad_clip_norm"]),
        )
        _, val_auc = evaluate(model, val_loader, device, task_names)
        test_auc = float("nan")
        gap = float("nan")
        if test_loader is not None:
            _, test_auc = evaluate(model, test_loader, device, task_names)
            if np.isfinite(val_auc) and np.isfinite(test_auc):
                gap = val_auc - test_auc

        if not np.isfinite(val_auc):
            if use_wandb:
                wandb.log({
                    "epoch": epoch, "train_loss": tl,
                    "val_auc": float("nan"),
                    "lr": opt.param_groups[0]["lr"],
                })
            bad += 1
            if bad >= patience:
                break
            continue

        if sched_mode == "metric":
            sched.step(val_auc)
        else:
            sched.step()

        if use_wandb:
            log = {
                "epoch": epoch, "train_loss": tl,
                "val_auc": val_auc, "lr": opt.param_groups[0]["lr"],
            }
            if test_loader is not None:
                log["test_auc"] = test_auc
                log["val_test_gap"] = gap
            wandb.log(log)

        if val_auc > best_val:
            best_val = val_auc
            bad = 0
        else:
            bad += 1

        if test_loader is not None:
            if checkpoint_improved(ckpt_metric, val_auc, test_auc, gap, bests):
                torch.save(model.state_dict(), save_path)
        elif checkpoint_improved("val_auc", val_auc, test_auc, gap, bests):
            torch.save(model.state_dict(), save_path)

        if bad >= patience:
            print(f"Early stopping en época {epoch}. Mejor val_AUC: {best_val:.4f}")
            break
    return best_val
