"""GNNExplainer (PyG) — docs/05_xai.md."""

from __future__ import annotations

import torch
from torch_geometric.data import Data

try:
    from torch_geometric.explain import Explainer, GNNExplainer as PyGExplainer
except Exception:  # pragma: no cover
    Explainer = None  # type: ignore[misc, assignment]
    PyGExplainer = None  # type: ignore[misc, assignment]


def build_explainer(model: torch.nn.Module) -> "Explainer":
    if Explainer is None or PyGExplainer is None:
        raise ImportError("torch_geometric.explain no disponible en esta instalación")
    return Explainer(
        model=model,
        algorithm=PyGExplainer(epochs=200, lr=0.01),
        explanation_type="model",
        node_mask_type="attributes",
        edge_mask_type="object",
        model_config=dict(
            mode="binary_classification",
            task_level="graph",
            return_type="raw",
        ),
    )


def explain_molecule(
    explainer: "Explainer",
    data: Data,
    task_index: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    batch = torch.zeros(data.x.size(0), dtype=torch.long, device=data.x.device)
    explanation = explainer(
        x=data.x,
        edge_index=data.edge_index,
        batch=batch,
        target=torch.tensor([task_index], device=data.x.device, dtype=torch.long),
    )
    nm = explanation.node_mask
    em = explanation.edge_mask
    if nm is None:
        raise RuntimeError("GNNExplainer no devolvió node_mask")
    node_imp = nm.squeeze()
    if node_imp.dim() > 1:
        node_imp = node_imp.mean(dim=-1)
    edge_imp = em if em is not None else torch.zeros(data.edge_index.size(1), device=data.x.device)
    return node_imp, edge_imp
