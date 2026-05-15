"""ToxicityDataset PyG y TASK_NAMES (AGENTS.md regla 7)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import torch
from torch.utils.data import Dataset
from torch_geometric.data import Data

# Orden alineado con DeepChem molnet.load_tox21 tasks
TASK_NAMES: list[str] = [
    "NR-AR",
    "NR-AR-LBD",
    "NR-AhR",
    "NR-Aromatase",
    "NR-ER",
    "NR-ER-LBD",
    "NR-PPAR-gamma",
    "SR-ARE",
    "SR-AtAD5",
    "SR-HSE",
    "SR-MMP",
    "SR-p53",
]

N_TASKS = len(TASK_NAMES)


class ToxicityDataset(Dataset):
    """Carga listas de `Data` desde `root/graphs_{split}.pt` (docs/01_pipeline_datos.md)."""

    def __init__(self, root: str | Path, split: Literal["train", "val", "test"]) -> None:
        self.root = Path(root)
        self.split = split
        path = self.root / f"graphs_{split}.pt"
        if not path.is_file():
            raise FileNotFoundError(
                f"No existe {path}. Ejecuta: python scripts/prepare_tox21_graphs.py"
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
