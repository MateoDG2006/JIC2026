"""
Grad-CAM adaptado para grafos moleculares.

Calcula la importancia de cada átomo para una predicción específica,
usando gradientes y activaciones de la última capa GIN.

Cómo funciona:
  1. Pasa la molécula por el modelo (forward) y GRABA las activaciones
     de la última capa GIN usando un "hook"
  2. Calcula el gradiente de la predicción respecto a esas activaciones (backward)
  3. Para cada canal k: α[k] = promedio del gradiente sobre todos los nodos
     → "¿qué tan importante es este canal para la predicción?"
  4. Importancia(v) = ReLU(Σ_k α[k] × activación[v][k])
     → "¿este átomo activó canales importantes?"
  5. Normaliza a [0, 1]

Es mucho más rápido que GNNExplainer (1 pasada vs 200 iteraciones)
pero más ruidoso.
"""

from __future__ import annotations

import torch
from torch_geometric.data import Data


def grad_cam_graph(
    model: torch.nn.Module,
    data: Data,
    task_index: int,
    batch: torch.Tensor | None = None,
) -> torch.Tensor:
    """
    Calcula importancia por átomo usando Grad-CAM sobre la última capa GIN.

    Args:
        model: modelo GINToxicity entrenado
        data: grafo molecular (un solo Data)
        task_index: índice de la tarea (0-11) para la cual explicar
        batch: tensor de batch (si es None, asume una sola molécula)

    Returns:
        cam: tensor (num_átomos,) con importancia normalizada en [0, 1]
    """
    if batch is None:
        batch = torch.zeros(data.x.size(0), dtype=torch.long, device=data.x.device)
    device = data.x.device
    batch = batch.to(device)

    # Diccionario para guardar las activaciones capturadas por el hook
    act_store: dict[str, torch.Tensor] = {}

    def fwd_hook(
        module: torch.nn.Module, inp: tuple, out: torch.Tensor
    ) -> None:
        """Hook que se ejecuta DURANTE el forward pass para grabar activaciones."""
        out.retain_grad()  # necesario para calcular gradientes después
        act_store["a"] = out

    # Verificar que el modelo tiene capas GIN
    if not hasattr(model, "gin_layers") or len(model.gin_layers) == 0:
        raise ValueError("model debe tener atributo gin_layers (GINToxicity)")

    # Instalar el hook en la ÚLTIMA capa GIN
    layer = model.gin_layers[-1]

    # Eval mode: explicamos 1 molécula → batch grafo = 1. En train(),
    # BatchNorm del clasificador falla con tensor (1, hidden_dim).
    was_training = model.training
    model.eval()

    h = layer.register_forward_hook(fwd_hook)
    try:
        edge_attr = data.edge_attr if hasattr(data, "edge_attr") else None
        with torch.enable_grad():
            logits = model(data.x, data.edge_index, batch, edge_attr=edge_attr)
            model.zero_grad(set_to_none=True)
            logits[0, task_index].backward()
    finally:
        h.remove()
        if was_training:
            model.train()
        else:
            model.eval()

    # Obtener activaciones y sus gradientes
    act = act_store.get("a")
    if act is None or act.grad is None:
        return torch.zeros(data.x.size(0), device=device)

    # Grad-CAM: multiplicar activación × gradiente y sumar canales
    # cam[v] = ReLU(Σ_k activación[v][k] × gradiente[v][k])
    cam = torch.relu((act * act.grad).sum(dim=1))

    # Normalizar a [0, 1]
    cam = cam - cam.min()
    denom = cam.max().item() + 1e-8
    cam = cam / denom

    return cam.detach()
