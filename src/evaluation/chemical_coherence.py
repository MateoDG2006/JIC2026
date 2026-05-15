"""Validación química de explicaciones — docs/05_xai.md."""

from __future__ import annotations

import numpy as np
from rdkit.Chem import MolFromSmarts, MolFromSmiles

TOXIC_GROUPS: dict[str, list[str]] = {
    "NR-AR": ["[#6]-[#6](=O)-[#8]", "[OH]", "[NH2]"],
    "NR-AR-LBD": ["[#6]-[#6](=O)-[#8]", "[OH]", "c1ccccc1"],
    "NR-AhR": ["c1ccccc1", "c1ccncc1", "c1ccoc1"],
    "NR-Aromatase": ["n1ccnc1", "n1cncn1", "[Cl]", "C(F)(F)F"],
    "NR-ER": ["c1ccccc1[OH]", "[NH2]", "[OH]"],
    "NR-ER-LBD": ["c1ccccc1[OH]", "[NH2]", "[OH]"],
    "NR-PPAR-gamma": ["C(=O)O", "c1ccccc1", "CCCC"],
    "SR-ARE": ["[P](=S)", "[N+](=O)[O-]", "[Cl]", "C=C"],
    "SR-AtAD5": ["[N+](=O)[O-]", "[Cl]", "C=C", "[Br]"],
    "SR-HSE": ["C(=O)C", "CC(C)C", "c1ccccc1"],
    "SR-MMP": ["[P](=S)", "c1ccccc1", "[N+](=O)[O-]"],
    "SR-p53": ["[N+](=O)[O-]", "C=C", "[Cl]"],
}


def precision_at_k(
    smiles: str,
    node_importance: np.ndarray,
    task_name: str,
    k: int = 3,
) -> int:
    mol = MolFromSmiles(smiles)
    if mol is None:
        return 0
    top_k_atoms = np.argsort(node_importance)[-k:]
    expected = TOXIC_GROUPS.get(task_name, [])
    for pattern in expected:
        query = MolFromSmarts(pattern)
        if query is None:
            continue
        matches = mol.GetSubstructMatches(query)
        matched_atoms = {a for match in matches for a in match}
        if matched_atoms & set(top_k_atoms.tolist()):
            return 1
    return 0
