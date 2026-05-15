"""Genera `data/processed/graphs_{train,val,test}.pt` desde DeepChem Tox21.

Uso (desde la raíz del repo):
  python scripts/prepare_tox21_graphs.py

Requisitos: deepchem, rdkit, torch, torch_geometric.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch


def _first_smiles(x: object) -> str:
    """Una fila de RawFeaturizer puede ser str, ndarray (1,), (1,1), lista anidada, etc."""
    cur: object = x
    for _ in range(8):
        if cur is None:
            return ""
        if isinstance(cur, str):
            return cur
        if isinstance(cur, bytes):
            return cur.decode("utf-8", errors="replace")
        if isinstance(cur, (list, tuple)):
            if len(cur) == 0:
                return ""
            cur = cur[0]
            continue
        if isinstance(cur, np.ndarray):
            if cur.size == 0:
                return ""
            if cur.ndim == 0:
                cur = cur.item()
                continue
            cur = cur.flat[0]
            continue
        return str(cur)
    return str(cur)


def _itersample_to_smiles_y_w(sample: object) -> tuple[str, np.ndarray, np.ndarray]:
    """Convierte una fila de `DiskDataset.itersamples()` (suele ser `map`: mol, y, w, id/SMILES)."""
    from rdkit import Chem

    p = tuple(sample)
    if len(p) == 3:
        xi, yi, wi = p
        idi: object | None = None
    elif len(p) >= 4:
        xi, yi, wi, idi = p[0], p[1], p[2], p[3]
    else:
        raise ValueError(f"Muestra con {len(p)} elementos; se esperaban 3 o 4+ (x, y, w[, id]).")

    yi_arr = np.asarray(yi, dtype=np.float64).ravel()
    wi_arr = np.asarray(wi, dtype=np.float64).ravel()

    smi = ""
    if isinstance(xi, Chem.Mol):
        try:
            if xi.GetNumAtoms() > 0:
                smi = Chem.MolToSmiles(xi)
        except Exception:
            smi = ""
    if not smi:
        smi = _first_smiles(xi)
    if not smi and idi is not None:
        smi = str(idi)
    return smi, yi_arr, wi_arr


def _extract_smiles_y_mask(ds) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Usa `itersamples()`: `DiskDataset` no siempre admite `ds[i]` y `ds.X` puede ser 1D o irregular."""
    smiles: list[str] = []
    ys: list[np.ndarray] = []
    ws: list[np.ndarray] = []
    for sample in ds.itersamples():
        smi, yi_arr, wi_arr = _itersample_to_smiles_y_w(sample)
        smiles.append(smi)
        ys.append(yi_arr)
        ws.append(wi_arr)
    y = np.stack(ys, axis=0).astype(np.float64, copy=False) if ys else np.empty((0, 0), dtype=np.float64)
    w = np.stack(ws, axis=0).astype(np.float64, copy=False) if ws else np.empty((0, 0), dtype=np.float64)
    # Medición válida: peso > 0 y etiqueta finita (Tox21 usa NaN o w=0 para ausentes).
    mask = (w > 0) & np.isfinite(y)
    return smiles, y, mask.astype(bool)


def _build_list(smiles: list[str], y: np.ndarray, mask: np.ndarray) -> list:
    from torch_geometric.data import Data

    from src.data.featurizer import smiles_to_graph

    out: list[Data] = []
    for i, smi in enumerate(smiles):
        g = smiles_to_graph(smi, labels=y[i].tolist(), mask=mask[i].tolist())
        if g is not None:
            out.append(g)
    return out


def main() -> None:
    import deepchem as dc

    from src.data.splitter import save_split_indices

    _tasks, splits, _ = dc.molnet.load_tox21(
        featurizer=dc.feat.RawFeaturizer(),
        splitter="scaffold",
    )
    train_ds, val_ds, test_ds = splits

    proc = ROOT / "data" / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    splits_dir = ROOT / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    splits_map = {
        "train": train_ds,
        "val": val_ds,
        "test": test_ds,
    }
    for name, ds in splits_map.items():
        smi, y, m = _extract_smiles_y_mask(ds)
        graphs = _build_list(smi, y, m)
        torch.save(graphs, proc / f"graphs_{name}.pt")
        print(f"Guardado graphs_{name}.pt — {len(graphs)} grafos")

    n_train = len(train_ds)
    n_val = len(val_ds)
    n_test = len(test_ds)
    train_idx = list(range(0, n_train))
    val_idx = list(range(n_train, n_train + n_val))
    test_idx = list(range(n_train + n_val, n_train + n_val + n_test))
    save_split_indices(
        splits_dir / "scaffold_split_indices.json",
        train_idx,
        val_idx,
        test_idx,
        meta={
            "source": "deepchem_scaffold",
            "description": (
                "Índices fila a fila al concatenar train|val|test del DiskDataset DeepChem "
                "(no coinciden con filas omitidas al fallar SMILES→grafo)."
            ),
        },
    )
    print(f"Guardado data/splits/scaffold_split_indices.json ({n_train + n_val + n_test} índices)")

    print("Listo.")


if __name__ == "__main__":
    main()
