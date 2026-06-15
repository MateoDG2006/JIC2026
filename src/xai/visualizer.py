"""
Visualización de moléculas coloreadas por importancia XAI.

Dibuja la molécula como SVG donde cada átomo se colorea según
su importancia (resultado de GNNExplainer o Grad-CAM).
Rojo intenso = alta importancia, amarillo claro = baja importancia.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.cm as cm
import numpy as np
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D


def _get_cmap(name: str = "YlOrRd"):
    """Obtener colormap compatible con diferentes versiones de matplotlib."""
    try:
        return matplotlib.colormaps[name]
    except Exception:
        return cm.get_cmap(name)


def normalize_importance(node_importance: np.ndarray) -> np.ndarray:
    """Normaliza importancias a [0, 1] (misma lógica que el SVG)."""
    imp = np.asarray(node_importance, dtype=np.float64)
    return (imp - imp.min()) / (imp.max() - imp.min() + 1e-8)


def importance_to_hex_colors(
    node_importance: np.ndarray,
    cmap_name: str = "YlOrRd",
) -> list[str]:
    """Convierte importancias a colores hex idénticos al SVG (matplotlib YlOrRd)."""
    imp = normalize_importance(node_importance)
    colormap = _get_cmap(cmap_name)
    colors: list[str] = []
    for i in range(len(imp)):
        r, g, b = (float(x) for x in colormap(float(imp[i]))[:3])
        colors.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
    return colors


def draw_molecule_with_importance(
    smiles: str,
    node_importance: np.ndarray,
    title: str = "",
    save_path: str | Path | None = None,
) -> str:
    """
    Dibuja una molécula SVG con cada átomo coloreado por importancia.

    IMPORTANTE: node_importance debe estar en el MISMO orden de átomos
    que el grafo generado por featurizer.py. Ambos usan canonicalización
    de RDKit, así que los índices deberían coincidir.

    Args:
        smiles: SMILES de la molécula
        node_importance: array (num_átomos,) con valores de importancia
        title: título opcional (no se dibuja en el SVG)
        save_path: si se proporciona, guarda el SVG en este archivo

    Returns:
        String SVG con la molécula coloreada
    """
    # Canonicalizar una sola vez (misma canonicalización que featurizer.py)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"SMILES inválido: {smiles}")
    canon_smiles = Chem.MolToSmiles(mol)
    mol = Chem.MolFromSmiles(canon_smiles)

    # Verificar que el número de átomos coincide
    imp = np.asarray(node_importance, dtype=np.float64)
    n_atoms = mol.GetNumAtoms()
    if imp.shape[0] != n_atoms:
        raise ValueError(
            f"node_importance tiene {imp.shape[0]} valores pero la molécula "
            f"canónica tiene {n_atoms} átomos. Verifica que uses la misma "
            f"canonicalización que featurizer.py."
        )

    # Normalizar importancias a [0, 1] para el colormap
    imp = normalize_importance(imp)

    # Asignar color a cada átomo: amarillo (bajo) → rojo (alto)
    colormap = _get_cmap("YlOrRd")
    atom_cols = {
        i: tuple(float(x) for x in colormap(float(imp[i]))[:3])
        for i in range(n_atoms)
    }

    # Dibujar molécula como SVG
    drawer = rdMolDraw2D.MolDraw2DSVG(500, 400)
    drawer.drawOptions().addStereoAnnotation = False
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=list(range(n_atoms)),
        highlightBonds=[],
        highlightAtomColors=atom_cols,
        highlightBondColors={},
    )
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()

    # Guardar a disco si se indicó ruta
    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(svg, encoding="utf-8")

    return svg
