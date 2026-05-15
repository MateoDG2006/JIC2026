"""GNN-GIN multitarea — docs/02_modelo_gin.md."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GINConv, global_max_pool, global_mean_pool


class GINLayer(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.3, eps: float = 0.0) -> None:
        super().__init__()
        mlp = nn.Sequential(
            nn.Linear(in_dim, out_dim * 2),
            nn.BatchNorm1d(out_dim * 2),
            nn.ReLU(),
            nn.Linear(out_dim * 2, out_dim),
            nn.BatchNorm1d(out_dim),
        )
        self.conv = GINConv(mlp, eps=eps, train_eps=True)
        self.bn = nn.BatchNorm1d(out_dim)
        self.dropout = nn.Dropout(dropout)
        self.residual = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        out = self.conv(x, edge_index)
        out = F.relu(self.bn(out))
        out = self.dropout(out)
        return out + self.residual(x)


class GINToxicity(nn.Module):
    def __init__(
        self,
        node_feat_dim: int = 45,
        hidden_dim: int = 128,
        n_layers: int = 3,
        n_tasks: int = 12,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(node_feat_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        self.gin_layers = nn.ModuleList(
            [GINLayer(hidden_dim, hidden_dim, dropout=dropout) for _ in range(n_layers)]
        )
        readout_dim = hidden_dim * 2
        self.classifier = nn.Sequential(
            nn.Linear(readout_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, n_tasks),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(x)
        for layer in self.gin_layers:
            h = layer(h, edge_index)
        h_mean = global_mean_pool(h, batch)
        h_max = global_max_pool(h, batch)
        h_g = torch.cat([h_mean, h_max], dim=1)
        return self.classifier(h_g)
