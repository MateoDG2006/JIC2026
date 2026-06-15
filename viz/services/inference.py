"""Servicio de inferencia: carga el modelo GIN y ejecuta prediccion + XAI."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from viz.config import CONFIG_PATH, MODEL_PATH, TASK_NAMES

_model = None
_device = None
_model_error: str | None = None


def _load_config() -> dict[str, Any]:
    import yaml
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_device() -> torch.device:
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def model_available() -> bool:
    """Indica si el checkpoint del modelo existe en disco."""
    return MODEL_PATH.is_file()


def get_model_error() -> str | None:
    """Mensaje de error si el modelo no pudo cargarse."""
    return _model_error


def get_model():
    """Carga el modelo GIN entrenado (singleton, se carga una sola vez)."""
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error is not None:
        raise RuntimeError(_model_error)

    from src.models.gin import GINToxicity

    if not MODEL_PATH.is_file():
        _model_error = (
            f"No se encontro el modelo en {MODEL_PATH}. "
            "Ejecuta: make train-gin"
        )
        raise RuntimeError(_model_error)

    try:
        cfg = _load_config()["model"]
        device = get_device()

        model = GINToxicity(
            node_feat_dim=int(cfg["node_feat_dim"]),
            edge_feat_dim=int(cfg["edge_feat_dim"]),
            hidden_dim=int(cfg["hidden_dim"]),
            n_layers=int(cfg["n_layers"]),
            n_tasks=int(cfg["n_tasks"]),
            dropout=float(cfg["dropout"]),
        ).to(device)

        try:
            state = torch.load(MODEL_PATH, map_location=device, weights_only=True)
        except TypeError:
            state = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state)
        model.eval()
        _model = model
        return model
    except Exception as exc:
        _model_error = str(exc)
        raise RuntimeError(_model_error) from exc


def smiles_to_graph(smiles: str):
    """Convierte un SMILES a grafo PyG usando el featurizer del proyecto."""
    from src.data.featurizer import smiles_to_graph as _s2g
    return _s2g(smiles)


def predict(smiles: str) -> dict[str, float] | None:
    """Ejecuta prediccion del modelo sobre un SMILES.

    Retorna dict {task_name: probabilidad} o None si el SMILES es invalido.
    """
    graph = smiles_to_graph(smiles)
    if graph is None:
        return None

    model = get_model()
    device = get_device()

    graph = graph.to(device)
    batch = torch.zeros(graph.x.size(0), dtype=torch.long, device=device)
    edge_attr = graph.edge_attr if hasattr(graph, "edge_attr") else None

    with torch.no_grad():
        logits = model(graph.x, graph.edge_index, batch, edge_attr=edge_attr)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()

    return {name: float(round(p, 4)) for name, p in zip(TASK_NAMES, probs)}


def _tensor_to_importance(imp: torch.Tensor) -> list[float]:
    arr = imp.detach().cpu().numpy().astype(np.float64)
    arr_min, arr_max = arr.min(), arr.max()
    if arr_max - arr_min > 1e-8:
        arr = (arr - arr_min) / (arr_max - arr_min)
    else:
        arr = np.zeros_like(arr)
    return [float(round(v, 4)) for v in arr]


def explain_gnnexplainer(smiles: str, task_index: int) -> list[float] | None:
    """Genera importancia por atomo usando GNNExplainer para una tarea."""
    graph = smiles_to_graph(smiles)
    if graph is None:
        return None

    model = get_model()
    device = get_device()
    graph = graph.to(device)

    try:
        from src.xai.gnn_explainer import build_explainer, explain_molecule

        explainer = build_explainer(model, task_index)
        node_imp, _ = explain_molecule(explainer, graph)
        return _tensor_to_importance(node_imp)
    except Exception as e:
        print(f"[GNNExplainer] Error: {e}")
        return None


def explain_gradcam(smiles: str, task_index: int) -> list[float] | None:
    """Genera importancia por atomo usando Grad-CAM sobre la ultima capa GIN."""
    graph = smiles_to_graph(smiles)
    if graph is None:
        return None

    model = get_model()
    device = get_device()
    graph = graph.to(device)

    try:
        from src.xai.grad_cam import grad_cam_graph

        cam = grad_cam_graph(model, graph, task_index)
        return _tensor_to_importance(cam)
    except Exception as e:
        print(f"[Grad-CAM] Error: {e}")
        return None


def full_analysis(smiles: str) -> dict[str, Any] | None:
    """Ejecuta prediccion + XAI completo para un SMILES.

    Retorna dict con predictions, xai por tarea, y metadatos.
    """
    predictions = predict(smiles)
    if predictions is None:
        return None

    from viz.services.molecule import atom_symbols, molecular_properties

    props = molecular_properties(smiles)
    symbols = atom_symbols(smiles)

    top_task_idx = int(np.argmax([predictions[t] for t in TASK_NAMES]))
    top_task = TASK_NAMES[top_task_idx]

    xai_gnnexp: dict[str, list[float] | None] = {}
    xai_gradcam: dict[str, list[float] | None] = {}

    # XAI para la tarea con mayor prediccion (rapido) + las que superen 0.4
    tasks_to_explain = {top_task_idx}
    for i, t in enumerate(TASK_NAMES):
        if predictions[t] > 0.4:
            tasks_to_explain.add(i)

    for ti in tasks_to_explain:
        tname = TASK_NAMES[ti]
        xai_gnnexp[tname] = explain_gnnexplainer(smiles, ti)
        xai_gradcam[tname] = explain_gradcam(smiles, ti)

    from src.xai.visualizer import importance_to_hex_colors

    def _colors(imp: list[float] | None) -> list[str] | None:
        if imp is None:
            return None
        return importance_to_hex_colors(np.array(imp))

    xai_colors_gnnexp = {t: _colors(xai_gnnexp[t]) for t in xai_gnnexp}
    xai_colors_gradcam = {t: _colors(xai_gradcam[t]) for t in xai_gradcam}

    return {
        "smiles": props["canonical_smiles"] if props else smiles,
        "predictions": predictions,
        "top_task": top_task,
        "xai": {
            "gnnexplainer": xai_gnnexp,
            "gradcam": xai_gradcam,
        },
        "xai_colors": {
            "gnnexplainer": xai_colors_gnnexp,
            "gradcam": xai_colors_gradcam,
        },
        "atom_symbols": symbols,
        "properties": props,
    }
