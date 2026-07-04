"""
Scaffold split para división de datos moleculares.

Divide el dataset agrupando moléculas por su "scaffold" de Murcko
(el esqueleto molecular sin cadenas laterales). Esto garantiza que
moléculas con la misma estructura base NO aparezcan en train Y test,
lo que da una evaluación más realista de generalización.

Ejemplo: Aspirina y Ácido salicílico tienen el mismo scaffold (benceno
con grupo carboxílico), así que siempre van al mismo split.
"""

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
    """Divide los índices por scaffold de Murcko.

    Asigna scaffolds completos (nunca parte de un scaffold) a cada split.
    Scaffolds más grandes van primero a train para balancear tamaños.

    Args:
        smiles_list: lista de SMILES de todas las moléculas
        frac_train: fracción para entrenamiento (default 0.7)
        frac_val: fracción para validación (default 0.15)
        frac_test: fracción para prueba (default 0.15)

    Returns:
        Tupla (train_idx, val_idx, test_idx) con listas de índices
    """
    if abs(frac_train + frac_val + frac_test - 1.0) > 1e-6:
        raise ValueError("frac_train + frac_val + frac_test debe sumar 1")

    # Agrupar moléculas por su scaffold
    scaffolds: dict[str, list[int]] = defaultdict(list)
    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            # SMILES inválidos van a su propio "scaffold" ficticio
            scaffolds[f"__invalid__{i}"].append(i)
            continue
        sc = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
        scaffolds[sc].append(i)

    # Ordenar por tamaño descendente: scaffolds grandes van a train
    scaffold_sets = sorted(scaffolds.values(), key=len, reverse=True)
    n = len(smiles_list)
    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    # Asignar scaffolds completos a cada split
    for s in scaffold_sets:
        if len(train_idx) / n < frac_train:
            train_idx += s
        elif len(val_idx) / n < frac_val:
            val_idx += s
        elif frac_test > 1e-9 and len(test_idx) / n < frac_test:
            test_idx += s
        else:
            train_idx += s

    # Asegurar que no queden índices sin asignar
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
    """Guarda los índices de split en un archivo JSON."""
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
    """Carga los índices de split desde un archivo JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["train_idx"], data["val_idx"], data["test_idx"]
