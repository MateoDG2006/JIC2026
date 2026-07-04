"""Tests para cross-validation con scaffold split."""

import pytest

pytest.importorskip("rdkit")

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.evaluation.cross_validation import create_scaffold_folds


def _sc(smi: str) -> str:
    """Extrae el scaffold de Murcko."""
    m = Chem.MolFromSmiles(smi)
    assert m is not None
    return MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False)


def test_create_scaffold_folds_partitions_train_val():
    """Cada fold debe ser una partición completa de los índices."""
    smiles = ["CC", "CCO", "c1ccccc1", "c1ccccc1O", "CCC", "CCN", "CCCC"]
    tv = list(range(len(smiles)))
    folds = create_scaffold_folds(smiles, tv, n_folds=3, seed=1)
    assert len(folds) == 3
    for tr, va in folds:
        # Sin solapamiento entre train y val
        assert set(tr) & set(va) == set()
        # Todos los índices cubiertos
        assert set(tr) | set(va) == set(tv)


def test_create_scaffold_folds_no_scaffold_leak_across_train_val():
    """Ningún scaffold debe aparecer en train Y val del mismo fold."""
    smiles = ["CC", "CCO", "c1ccccc1", "c1ccccc1O", "CCC", "CCN"]
    tv = list(range(len(smiles)))
    folds = create_scaffold_folds(smiles, tv, n_folds=3, seed=2)
    for tr, va in folds:
        scaffolds_train = {_sc(smiles[i]) for i in tr}
        scaffolds_val = {_sc(smiles[i]) for i in va}
        assert not (scaffolds_train & scaffolds_val), \
            "Un scaffold aparece en train y val del mismo fold"
