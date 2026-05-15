"""Grad-CAM en grafos — docs/05_xai.md."""

from __future__ import annotations

import torch
from torch_geometric.data import Data


def grad_cam_graph(
    model: torch.nn.Module,
    data: Data,
    task_index: int,
    batch: torch.Tensor | None = None,
) -> torch.Tensor:
    """Importancia por nodo respecto a la última capa GIN (`model.gin_layers[-1]`)."""
    if batch is None:
        batch = torch.zeros(data.x.size(0), dtype=torch.long, device=data.x.device)
    device = data.x.device
    batch = batch.to(device)

    act_store: dict[str, torch.Tensor] = {}

    def fwd_hook(module: torch.nn.Module, inp: tuple, out: torch.Tensor) -> None:
        out.retain_grad()
        act_store["a"] = out

    if not hasattr(model, "gin_layers") or len(model.gin_layers) == 0:
        raise ValueError("model debe tener atributo gin_layers (GINToxicity)")
    layer = model.gin_layers[-1]
    model.eval()
    h = layer.register_forward_hook(fwd_hook)
    try:
        logits = model(data.x, data.edge_index, batch)
        model.zero_grad(set_to_none=True)
        logits[0, task_index].backward()
    finally:
        h.remove()

    act = act_store.get("a")
    if act is None or act.grad is None:
        return torch.zeros(data.x.size(0), device=device)
    cam = torch.relu((act * act.grad).sum(dim=1))
    cam = cam - cam.min()
    denom = cam.max().item() + 1e-8
    cam = cam / denom
    return cam.detach()
