"""Utilidades moleculares: SMILES a 3D, propiedades, SDF."""

from __future__ import annotations

from io import StringIO

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors


def smiles_to_sdf(smiles: str) -> str | None:
    """Convierte SMILES a SDF con coordenadas 3D (RDKit ETKDG).

    Retorna el bloque SDF como string, o None si falla.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        status = AllChem.EmbedMolecule(mol, AllChem.ETKDG())
    if status != 0:
        return None
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    mol = Chem.RemoveHs(mol)
    writer = Chem.SDWriter(StringIO())
    writer.SetForceV3000(False)
    buf = StringIO()
    writer = Chem.SDWriter(buf)
    writer.write(mol)
    writer.close()
    return buf.getvalue()


def smiles_to_mol_block(smiles: str) -> str | None:
    """Convierte SMILES a MOL block con coordenadas 3D (sin header SDF)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        status = AllChem.EmbedMolecule(mol, AllChem.ETKDG())
    if status != 0:
        return None
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    mol = Chem.RemoveHs(mol)
    return Chem.MolToMolBlock(mol)


def molecular_properties(smiles: str) -> dict | None:
    """Calcula propiedades fisicoquimicas basicas."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "hbd": Descriptors.NumHDonors(mol),
        "hba": Descriptors.NumHAcceptors(mol),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "num_atoms": mol.GetNumAtoms(),
        "num_heavy_atoms": mol.GetNumHeavyAtoms(),
        "canonical_smiles": Chem.MolToSmiles(mol),
    }


def atom_symbols(smiles: str) -> list[str]:
    """Retorna lista de simbolos atomicos en orden de RDKit."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    return [atom.GetSymbol() for atom in mol.GetAtoms()]
