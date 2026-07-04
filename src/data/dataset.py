"""
Dataset de toxicidad para PyTorch Geometric.

Carga los grafos moleculares pre-procesados (graphs_train.pt, etc.)
y los expone como un Dataset iterable compatible con DataLoader de PyG.

También define TASK_NAMES: los nombres de las 12 tareas de toxicidad
de Tox21, en el mismo orden que las columnas de las etiquetas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import torch
from torch.utils.data import Dataset
from torch_geometric.data import Data

# Las 12 dianas biológicas de Tox21, en el orden de DeepChem.
# Este orden es CRÍTICO: las columnas de y (etiquetas) siguen este orden.
TASK_NAMES: list[str] = [
    "NR-AR",           # Receptor de andrógenos
    "NR-AR-LBD",       # Dominio ligando del receptor de andrógenos
    "NR-AhR",          # Receptor aril-hidrocarburo
    "NR-Aromatase",    # Aromatasa (CYP19)
    "NR-ER",           # Receptor de estrógenos
    "NR-ER-LBD",       # Dominio ligando del receptor de estrógenos
    "NR-PPAR-gamma",   # Receptor PPAR-γ (metabolismo)
    "SR-ARE",          # Respuesta antioxidante (estrés oxidativo)
    "SR-AtAD5",        # Daño al ADN
    "SR-HSE",          # Estrés por calor
    "SR-MMP",          # Potencial de membrana mitocondrial
    "SR-p53",          # Vía p53 (daño al ADN / carcinogénesis)
]

N_TASKS = len(TASK_NAMES)


class ToxicityDataset(Dataset):
    """Carga grafos moleculares desde archivos .pt pre-procesados.

    Los archivos se generan con scripts/fase1/prepare_tox21_graphs.py y contienen
    listas de objetos Data de PyG, cada uno con:
      - x: features de nodos (átomos)
      - edge_index: conectividad
      - edge_attr: features de aristas (enlaces)
      - y: etiquetas de toxicidad (12 tareas)
      - mask: máscara de mediciones válidas

    Args:
        root: directorio donde están los archivos .pt (data/processed/)
        split: "train", "val" o "test"
    """

    def __init__(self, root: str | Path, split: Literal["train", "val", "test"]) -> None:
        self.root = Path(root)
        self.split = split
        path = self.root / f"graphs_{split}.pt"
        if not path.is_file():
            raise FileNotFoundError(
                f"No existe {path}. Ejecuta: python scripts/fase1/prepare_tox21_graphs.py"
            )
        try:
            raw = torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:
            raw = torch.load(path, map_location="cpu")
        if not isinstance(raw, list):
            raise TypeError(f"Se esperaba list[Data] en {path}")
        self._data_list: list[Data] = raw

    def __len__(self) -> int:
        return len(self._data_list)

    def __getitem__(self, idx: int) -> Data:
        return self._data_list[idx]
