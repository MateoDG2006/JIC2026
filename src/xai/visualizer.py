"""Visualización molecular — docs/05_xai.md."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.cm as cm
import numpy as np
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D


def _get_cmap(name: str = "YlOrRd"):
    try:
        return matplotlib.colormaps[name]
    except Exception:
        return cm.get_cmap(name)


def draw_molecule_with_importance(
    smiles: str,
    node_importance: np.ndarray,
    title: str = "",
    save_path: str | Path | None = None,
) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("SMILES inválido")
    mol = Chem.MolFromSmiles(Chem.MolToSmiles(mol))
    imp = np.asarray(node_importance, dtype=np.float64)
    n_atoms = mol.GetNumAtoms()
    if imp.shape[0] != n_atoms:
        raise ValueError(
            f"node_importance tiene {imp.shape[0]} valores pero la molécula "
            f"canónica tiene {n_atoms} átomos. Usa la misma ordenación que el grafo XAI."
        )
    imp = (imp - imp.min()) / (imp.max() - imp.min() + 1e-8)
    colormap = _get_cmap("YlOrRd")
    atom_cols = {i: tuple(float(x) for x in colormap(float(imp[i]))[:3]) for i in range(mol.GetNumAtoms())}

    drawer = rdMolDraw2D.MolDraw2DSVG(500, 400)
    drawer.drawOptions().addStereoAnnotation = False
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=list(range(mol.GetNumAtoms())),
        highlightBonds=[],
        highlightAtomColors=atom_cols,
        highlightBondColors={},
    )
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(svg, encoding="utf-8")
    return svg
