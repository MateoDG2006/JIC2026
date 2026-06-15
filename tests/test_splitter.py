"""Tests para scaffold split — división de datos por esqueleto molecular."""

import pytest

pytest.importorskip("rdkit")

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.data.splitter import scaffold_split


def _scaffold(smi: str) -> str:
    """Extrae el scaffold de Murcko de un SMILES."""
    mol = Chem.MolFromSmiles(smi)
    assert mol is not None
    return MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)


def test_scaffold_split_no_overlap():
    """Los 3 splits no deben tener índices en común y deben cubrirlos todos."""
    smiles = ["CCO", "CCN", "c1ccccc1", "c1ccccc1O", "C1CCCCC1", "C1CCCCC1C"]
    tr, va, te = scaffold_split(smiles, frac_train=0.5, frac_val=0.25, frac_test=0.25)
    # Todos los índices están cubiertos
    assert set(tr) | set(va) | set(te) == set(range(len(smiles)))
    # No hay solapamiento entre splits
    assert not (set(tr) & set(va))
    assert not (set(tr) & set(te))
    assert not (set(va) & set(te))


def test_scaffold_split_same_scaffold_same_split():
    """Moléculas con el mismo scaffold deben caer en el mismo split.
    Esto evita "data leakage" por similitud estructural."""
    smiles = ["c1ccccc1", "c1ccccc1O", "c1ccccc1N", "CCO", "CCN", "CCC"]
    tr, va, te = scaffold_split(smiles, frac_train=0.5, frac_val=0.25, frac_test=0.25)
    # Los 3 derivados de benceno tienen el mismo scaffold
    benz = {_scaffold(smiles[i]) for i in (0, 1, 2)}
    assert len(benz) == 1
    # Deben estar todos en el mismo split
    splits = [tr, va, te]
    for sp in splits:
        hit = [i for i in (0, 1, 2) if i in sp]
        assert len(hit) in (0, 3), "Scaffold bencénico partido entre splits"
