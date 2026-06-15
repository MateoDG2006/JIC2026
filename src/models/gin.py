"""
Modelo GNN-GIN para predicción multitarea de toxicidad.

Arquitectura:
  1. Proyección inicial: features de átomo (45-dim) → espacio oculto (d-dim)
  2. Message Passing: L capas GINEConv con conexiones residuales
  3. Readout global: concatenación de mean-pool + max-pool
  4. Clasificador: MLP que produce 12 probabilidades (una por diana Tox21)

Usa GINEConv (no GINConv) para aprovechar las 9 features de enlace
calculadas por featurizer.py (tipo de enlace, conjugación, anillo, estéreo).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GINEConv, global_max_pool, global_mean_pool


class GINLayer(nn.Module):
    """
    Una capa GIN con edge features, BatchNorm, Dropout y conexión residual.

    La ecuación GIN es:
      h_v^(l) = MLP( (1 + ε) · h_v^(l-1) + Σ_u ReLU(h_u^(l-1) + e_uv) )

    Donde e_uv son las features del enlace entre u y v.
    """

    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        edge_dim: int = 9,
        dropout: float = 0.3,
        eps: float = 0.0,
    ) -> None:
        super().__init__()

        # MLP interno del GIN: transforma la suma de vecinos
        mlp = nn.Sequential(
            nn.Linear(in_dim, out_dim * 2),
            nn.BatchNorm1d(out_dim * 2),
            nn.ReLU(),
            nn.Linear(out_dim * 2, out_dim),
            nn.BatchNorm1d(out_dim),
        )

        # GINEConv incorpora edge_attr en la agregación de vecinos
        self.conv = GINEConv(mlp, eps=eps, train_eps=True, edge_dim=edge_dim)
        self.bn = nn.BatchNorm1d(out_dim)
        self.dropout = nn.Dropout(dropout)

        # Si cambia la dimensión, proyectar el residual para que sumen
        self.residual = (
            nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        )

    def forward(
        self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor
    ) -> torch.Tensor:
        # Agregar información de vecinos (con edge features) y transformar
        out = self.conv(x, edge_index, edge_attr)
        out = F.relu(self.bn(out))
        out = self.dropout(out)
        # Conexión residual: evita over-smoothing en grafos profundos
        return out + self.residual(x)


class GINToxicity(nn.Module):
    """
    Modelo GNN-GIN completo para predicción multitarea de toxicidad.

    Recibe un grafo molecular (átomos como nodos, enlaces como aristas)
    y produce 12 logits — uno por cada diana biológica de Tox21.

    Parámetros:
        node_feat_dim: dimensión de features por átomo (default 45, de featurizer.py)
        edge_feat_dim: dimensión de features por enlace (default 9, de featurizer.py)
        hidden_dim: dimensión del espacio oculto (128 o 256)
        n_layers: número de capas GIN (3 a 5)
        n_tasks: número de tareas de salida (12 para Tox21)
        dropout: probabilidad de dropout (0.3 a 0.5)
    """

    def __init__(
        self,
        node_feat_dim: int = 45,
        edge_feat_dim: int = 9,
        hidden_dim: int = 128,
        n_layers: int = 3,
        n_tasks: int = 12,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()

        # Bloque 1: proyectar features crudos al espacio oculto
        self.input_proj = nn.Sequential(
            nn.Linear(node_feat_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )

        # Bloque 2: capas de message passing GIN
        self.gin_layers = nn.ModuleList(
            [
                GINLayer(hidden_dim, hidden_dim, edge_dim=edge_feat_dim, dropout=dropout)
                for _ in range(n_layers)
            ]
        )

        # Bloque 3+4: readout global (mean + max) → clasificador MLP
        readout_dim = hidden_dim * 2  # concatenamos mean y max pooling
        self.classifier = nn.Sequential(
            nn.Linear(readout_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, n_tasks),  # 12 logits (sin sigmoid aquí)
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Args:
            x: features de nodos (num_nodos_total, 45)
            edge_index: conexiones (2, num_aristas_total)
            batch: índice de molécula por nodo (num_nodos_total,)
            edge_attr: features de aristas (num_aristas_total, 9), opcional

        Returns:
            logits: (batch_size, 12) — aplicar sigmoid para probabilidades
        """
        # Proyectar features de átomos al espacio oculto
        h = self.input_proj(x)

        # Message passing: cada capa agrega info de vecinos
        for layer in self.gin_layers:
            h = layer(h, edge_index, edge_attr)

        # Readout: resumir todos los nodos en un vector por molécula
        h_mean = global_mean_pool(h, batch)  # (batch_size, hidden_dim)
        h_max = global_max_pool(h, batch)  # (batch_size, hidden_dim)
        h_g = torch.cat([h_mean, h_max], dim=1)  # (batch_size, 2*hidden_dim)

        # Clasificador: producir 12 logits
        return self.classifier(h_g)
