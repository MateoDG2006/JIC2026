"""SMILES → grafo PyG (docs/01_pipeline_datos.md, AGENTS.md)."""

from __future__ import annotations

from typing import Sequence

import torch
from rdkit import Chem
from torch_geometric.data import Data

ATOM_TYPES: list[str] = ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "other"]
HYBRIDIZATION: list[Chem.rdchem.HybridizationType] = [
    Chem.rdchem.HybridizationType.S,
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]
BOND_TYPES: list[Chem.rdchem.BondType] = [
    Chem.rdchem.BondType.SINGLE,
    Chem.rdchem.BondType.DOUBLE,
    Chem.rdchem.BondType.TRIPLE,
    Chem.rdchem.BondType.AROMATIC,
]
BOND_STEREO: list[Chem.rdchem.BondStereo] = [
    Chem.rdchem.BondStereo.STEREONONE,
    Chem.rdchem.BondStereo.STEREOE,
    Chem.rdchem.BondStereo.STEREOZ,
]


def _one_hot(index: int, size: int) -> list[float]:
    return [1.0 if i == index else 0.0 for i in range(size)]


def _one_hot_value(value, choices: Sequence) -> list[float]:
    try:
        idx = choices.index(value)
    except ValueError:
        idx = len(choices) - 1
    return _one_hot(idx, len(choices))


def ring_size_features(atom: Chem.Atom) -> list[float]:
    """One-hot 6 posiciones: anillos de tamaño 3–7 y ≥8 (docs/01)."""
    out = [0.0] * 6
    if not atom.IsInRing():
        return out
    mol = atom.GetOwningMol()
    sizes: list[int] = []
    for ring in mol.GetRingInfo().AtomRings():
        if atom.GetIdx() in ring:
            sizes.append(len(ring))
    if not sizes:
        return out
    n = min(sizes)
    n = max(3, min(n, 8))
    out[min(n - 3, 5)] = 1.0
    return out


def atom_features(atom: Chem.Atom) -> list[float]:
    sym = atom.GetSymbol()
    sym_idx = ATOM_TYPES.index(sym) if sym in ATOM_TYPES else len(ATOM_TYPES) - 1
    feat: list[float] = []
    feat += _one_hot(sym_idx, len(ATOM_TYPES))
    feat += _one_hot(min(atom.GetDegree(), 10), 11)
    feat += _one_hot_value(atom.GetHybridization(), HYBRIDIZATION)
    feat += [float(atom.GetIsAromatic())]
    feat += _one_hot(min(atom.GetTotalNumHs(), 4), 5)
    feat += _one_hot({-2: 0, -1: 1, 0: 2, 1: 3, 2: 4}.get(atom.GetFormalCharge(), 2), 5)
    feat += [float(atom.IsInRing())]
    feat += ring_size_features(atom)
    return feat


def bond_features(bond: Chem.Bond) -> list[float]:
    feat: list[float] = []
    feat += _one_hot_value(bond.GetBondType(), BOND_TYPES)
    feat += [float(bond.GetIsConjugated())]
    feat += [float(bond.IsInRing())]
    feat += _one_hot_value(bond.GetStereo(), BOND_STEREO)
    return feat


NODE_FEAT_DIM = len(atom_features(Chem.MolFromSmiles("C").GetAtomWithIdx(0)))
_bond = Chem.MolFromSmiles("CC")
assert _bond is not None
EDGE_FEAT_DIM = len(bond_features(_bond.GetBondBetweenAtoms(0, 1)))
assert NODE_FEAT_DIM == 45, (
    f"NODE_FEAT_DIM esperado 45, obtenido {NODE_FEAT_DIM}. Revisa atom_features()."
)
assert EDGE_FEAT_DIM == 9, (
    f"EDGE_FEAT_DIM esperado 9, obtenido {EDGE_FEAT_DIM}. Revisa bond_features()."
)


def smiles_to_graph(
    smiles: str,
    labels: Sequence[float] | None = None,
    mask: Sequence[bool] | None = None,
) -> Data | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    smiles_canon = Chem.MolToSmiles(mol)
    mol = Chem.MolFromSmiles(smiles_canon)
    if mol is None:
        return None

    x = torch.tensor([atom_features(a) for a in mol.GetAtoms()], dtype=torch.float)
    edge_index: list[list[int]] = []
    edge_attr: list[list[float]] = []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        feat = bond_features(bond)
        edge_index += [[i, j], [j, i]]
        edge_attr += [feat, feat]

    if not edge_index:
        edge_index_t = torch.empty((2, 0), dtype=torch.long)
        edge_attr_t = torch.empty((0, EDGE_FEAT_DIM), dtype=torch.float)
    else:
        edge_index_t = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_attr_t = torch.tensor(edge_attr, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index_t, edge_attr=edge_attr_t)
    if labels is not None:
        y = torch.tensor(labels, dtype=torch.float)
        y = torch.nan_to_num(y, nan=0.0)
        data.y = y
    if mask is not None:
        data.mask = torch.tensor(mask, dtype=torch.bool)
    return data
