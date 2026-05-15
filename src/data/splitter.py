"""Scaffold split Murcko (AGENTS.md, docs/01_pipeline_datos.md)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold


def scaffold_split(
    smiles_list: list[str],
    frac_train: float = 0.7,
    frac_val: float = 0.15,
    frac_test: float = 0.15,
) -> tuple[list[int], list[int], list[int]]:
    """Asigna índices por scaffold; orden de scaffolds por tamaño descendente."""
    if abs(frac_train + frac_val + frac_test - 1.0) > 1e-6:
        raise ValueError("frac_train + frac_val + frac_test debe sumar 1")

    scaffolds: dict[str, list[int]] = defaultdict(list)
    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            scaffolds[f"__invalid__{i}"].append(i)
            continue
        sc = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
        scaffolds[sc].append(i)

    scaffold_sets = sorted(scaffolds.values(), key=len, reverse=True)
    n = len(smiles_list)
    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    for s in scaffold_sets:
        if len(train_idx) / n < frac_train:
            train_idx += s
        elif len(val_idx) / n < frac_val:
            val_idx += s
        elif frac_test > 1e-9 and len(test_idx) / n < frac_test:
            test_idx += s
        else:
            train_idx += s

    missing = set(range(n)) - set(train_idx) - set(val_idx) - set(test_idx)
    for i in sorted(missing):
        if len(train_idx) / n < frac_train:
            train_idx.append(i)
        elif len(val_idx) / n < frac_val:
            val_idx.append(i)
        else:
            test_idx.append(i)

    return train_idx, val_idx, test_idx


def save_split_indices(
    path: str | Path,
    train_idx: list[int],
    val_idx: list[int],
    test_idx: list[int],
    meta: dict[str, Any] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
    }
    if meta:
        payload["meta"] = meta
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_split_indices(path: str | Path) -> tuple[list[int], list[int], list[int]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["train_idx"], data["val_idx"], data["test_idx"]
