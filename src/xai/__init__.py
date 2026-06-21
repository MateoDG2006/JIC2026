"""Explainable AI sobre la GNN-GIN: GNNExplainer y Grad-CAM.

Submódulos:
    gnn_explainer  — Optimización de máscara nodo+arista (Ying et al. NeurIPS 2019)
    grad_cam       — Importancia atómica vía gradiente sobre la última capa GIN
    visualizer     — Renderizado SVG de la molécula con átomos coloreados por XAI

Ambos métodos producen un vector ``node_importance`` ∈ [0,1] de longitud N
(número de átomos), donde el índice coincide con la canonicalización RDKit
usada por ``featurizer.smiles_to_graph``.
"""

from src.xai.gnn_explainer import build_explainer, explain_molecule
from src.xai.grad_cam import grad_cam_graph
from src.xai.visualizer import draw_molecule_with_importance

__all__ = ["build_explainer", "explain_molecule", "grad_cam_graph", "draw_molecule_with_importance"]
