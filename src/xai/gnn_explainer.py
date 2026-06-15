"""
GNNExplainer — genera explicaciones para predicciones de la GNN.

Funciona optimizando una "máscara" sobre el grafo: busca el subgrafo
más pequeño que produce la misma predicción que el grafo completo.

Internamente:
  1. Crea una máscara continua M ∈ [0,1] para nodos y aristas
  2. Aplica la máscara al grafo: x_masked = x * M
  3. Pasa el grafo enmascarado por el modelo (congelado)
  4. Minimiza: -log(pred_masked) + λ·||M||₁
     → que la predicción se mantenga (fidelidad)
     → que la máscara use pocos nodos (parsimonia)
  5. Repite 200 iteraciones de optimización
  6. Resultado: los nodos con M ≈ 1 son los "importantes"
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch_geometric.data import Data

try:
    from torch_geometric.explain import Explainer, GNNExplainer as PyGExplainer
except Exception:  # pragma: no cover
    Explainer = None  # type: ignore[misc, assignment]
    PyGExplainer = None  # type: ignore[misc, assignment]


class _SingleTaskWrapper(nn.Module):
    """
    Wrapper que hace que el modelo multitarea (12 salidas) se comporte
    como si tuviera una sola salida — la de la tarea que queremos explicar.

    Esto es necesario porque PyG Explainer espera un modelo con una sola
    salida binaria, pero GINToxicity retorna 12 logits simultáneamente.
    """

    def __init__(self, model: nn.Module, task_index: int) -> None:
        super().__init__()
        self.model = model
        self.task_index = task_index

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        # Obtener los 12 logits y quedarnos solo con la tarea deseada
        logits = self.model(x, edge_index, batch, edge_attr=edge_attr)
        return logits[:, self.task_index].unsqueeze(-1)


def build_explainer(model: torch.nn.Module, task_index: int = 0) -> "Explainer":
    """
    Construye un Explainer de PyG para UNA tarea específica.

    Args:
        model: modelo GINToxicity ya entrenado (NO se modifican sus pesos)
        task_index: índice de la tarea a explicar (0-11)

    Returns:
        Explainer listo para usar con explain_molecule()
    """
    if Explainer is None or PyGExplainer is None:
        raise ImportError("torch_geometric.explain no disponible en esta instalación")

    # Envolver el modelo para que solo retorne la tarea deseada
    wrapped = _SingleTaskWrapper(model, task_index)

    return Explainer(
        model=wrapped,
        algorithm=PyGExplainer(epochs=200, lr=0.01),
        explanation_type="model",
        node_mask_type="attributes",  # máscara sobre features de nodos
        edge_mask_type="object",  # máscara sobre aristas completas
        model_config=dict(
            mode="binary_classification",
            task_level="graph",
            return_type="raw",  # el modelo retorna logits (sin sigmoid)
        ),
    )


def explain_molecule(
    explainer: "Explainer",
    data: Data,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Genera la explicación XAI para una molécula.

    Args:
        explainer: Explainer construido con build_explainer()
        data: grafo molecular (un solo Data de PyG)

    Returns:
        node_importance: tensor (num_átomos,) con valores en [0,1]
        edge_importance: tensor (num_aristas,) con valores en [0,1]
    """
    # Batch de una sola molécula: todos los nodos pertenecen al grafo 0
    batch = torch.zeros(data.x.size(0), dtype=torch.long, device=data.x.device)

    # Ejecutar GNNExplainer: 200 iteraciones de optimización de máscara
    explanation = explainer(
        x=data.x,
        edge_index=data.edge_index,
        batch=batch,
        edge_attr=data.edge_attr if hasattr(data, "edge_attr") else None,
    )

    # Extraer máscaras de nodos y aristas
    nm = explanation.node_mask
    em = explanation.edge_mask
    if nm is None:
        raise RuntimeError("GNNExplainer no devolvió node_mask")

    # Si la máscara tiene múltiples columnas (una por feature), promediar
    node_imp = nm.squeeze()
    if node_imp.dim() > 1:
        node_imp = node_imp.mean(dim=-1)

    # Si no hay máscara de aristas, crear una de ceros
    edge_imp = (
        em
        if em is not None
        else torch.zeros(data.edge_index.size(1), device=data.x.device)
    )

    return node_imp, edge_imp
