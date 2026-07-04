"""
Conversión de SMILES a grafos moleculares para PyTorch Geometric.

Este módulo es el corazón del pipeline de datos: toma una cadena SMILES
(representación textual de una molécula) y la convierte en un objeto Data
de PyG, donde:
  - Cada NODO es un átomo con un vector de 45 características
  - Cada ARISTA es un enlace químico con un vector de 9 características

Las características capturan propiedades químicas relevantes para la
predicción de toxicidad: tipo de átomo, hibridación, aromaticidad,
tipo de enlace, conjugación, etc.
"""

from __future__ import annotations

from typing import Sequence

import torch
from rdkit import Chem
from torch_geometric.data import Data

# ── Vocabularios de propiedades químicas ──────────────────────────────────

# Los 9 tipos de átomo más frecuentes en moléculas orgánicas + "other"
ATOM_TYPES: list[str] = ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "other"]

# Tipos de hibridación orbital (geometría del átomo)
HYBRIDIZATION: list[Chem.rdchem.HybridizationType] = [
    Chem.rdchem.HybridizationType.S,      # sin hibridación
    Chem.rdchem.HybridizationType.SP,      # lineal (180°)
    Chem.rdchem.HybridizationType.SP2,     # trigonal plana (120°)
    Chem.rdchem.HybridizationType.SP3,     # tetraédrica (109.5°)
    Chem.rdchem.HybridizationType.SP3D,    # bipiramidal trigonal
    Chem.rdchem.HybridizationType.SP3D2,   # octaédrica
]

# Tipos de enlace químico
BOND_TYPES: list[Chem.rdchem.BondType] = [
    Chem.rdchem.BondType.SINGLE,    # enlace simple (C-C)
    Chem.rdchem.BondType.DOUBLE,    # enlace doble (C=C)
    Chem.rdchem.BondType.TRIPLE,    # enlace triple (C≡C)
    Chem.rdchem.BondType.AROMATIC,  # enlace aromático (benceno)
]

# Estereoquímica del enlace (geometría cis/trans)
BOND_STEREO: list[Chem.rdchem.BondStereo] = [
    Chem.rdchem.BondStereo.STEREONONE,  # sin estereoquímica
    Chem.rdchem.BondStereo.STEREOE,     # configuración E (trans)
    Chem.rdchem.BondStereo.STEREOZ,     # configuración Z (cis)
]


# ── Funciones auxiliares de codificación ──────────────────────────────────

def _one_hot(index: int, size: int) -> list[float]:
    """Codifica un índice como vector one-hot de tamaño `size`."""
    return [1.0 if i == index else 0.0 for i in range(size)]


def _one_hot_value(value, choices: Sequence) -> list[float]:
    """Codifica un valor como one-hot buscándolo en la lista `choices`.
    Si no está, usa la última posición (categoría "otro")."""
    try:
        idx = choices.index(value)
    except ValueError:
        idx = len(choices) - 1
    return _one_hot(idx, len(choices))


def ring_size_features(atom: Chem.Atom) -> list[float]:
    """Vector de 6 posiciones indicando el tamaño del anillo más pequeño
    al que pertenece el átomo: [3, 4, 5, 6, 7, ≥8]."""
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


# ── Extracción de características ─────────────────────────────────────────

def atom_features(atom: Chem.Atom) -> list[float]:
    """Extrae un vector de 45 características para un átomo.

    Composición del vector:
      [0:10]  tipo de átomo (one-hot, 10 categorías)
      [10:21] grado (número de vecinos, one-hot 0-10)
      [21:27] hibridación orbital (one-hot, 6 categorías)
      [27]    es aromático (0 o 1)
      [28:33] número de hidrógenos (one-hot 0-4)
      [33:38] carga formal (one-hot -2 a +2)
      [38]    está en un anillo (0 o 1)
      [39:45] tamaño del anillo más pequeño (one-hot 3-8)
    """
    sym = atom.GetSymbol()
    sym_idx = ATOM_TYPES.index(sym) if sym in ATOM_TYPES else len(ATOM_TYPES) - 1
    feat: list[float] = []
    feat += _one_hot(sym_idx, len(ATOM_TYPES))                                      # 10
    feat += _one_hot(min(atom.GetDegree(), 10), 11)                                  # 11
    feat += _one_hot_value(atom.GetHybridization(), HYBRIDIZATION)                   # 6
    feat += [float(atom.GetIsAromatic())]                                            # 1
    feat += _one_hot(min(atom.GetTotalNumHs(), 4), 5)                                # 5
    feat += _one_hot({-2: 0, -1: 1, 0: 2, 1: 3, 2: 4}.get(atom.GetFormalCharge(), 2), 5)  # 5
    feat += [float(atom.IsInRing())]                                                 # 1
    feat += ring_size_features(atom)                                                 # 6
    return feat                                                                      # total: 45


def bond_features(bond: Chem.Bond) -> list[float]:
    """Extrae un vector de 9 características para un enlace químico.

    Composición del vector:
      [0:4] tipo de enlace (simple/doble/triple/aromático)
      [4]   es conjugado (0 o 1)
      [5]   está en un anillo (0 o 1)
      [6:9] estereoquímica (ninguna/E/Z)
    """
    feat: list[float] = []
    feat += _one_hot_value(bond.GetBondType(), BOND_TYPES)   # 4
    feat += [float(bond.GetIsConjugated())]                   # 1
    feat += [float(bond.IsInRing())]                          # 1
    feat += _one_hot_value(bond.GetStereo(), BOND_STEREO)     # 3
    return feat                                                # total: 9


# ── Verificación de dimensiones al importar ───────────────────────────────
# Se ejecuta al hacer `import featurizer` para detectar errores temprano.
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


# ── Conversión principal: SMILES → Data de PyG ───────────────────────────

def smiles_to_graph(
    smiles: str,
    labels: Sequence[float] | None = None,
    mask: Sequence[bool] | None = None,
) -> Data | None:
    """Convierte un SMILES en un objeto Data de PyTorch Geometric.

    Pasos:
      1. Parsear el SMILES con RDKit
      2. Canonicalizar (para que el orden de átomos sea determinístico)
      3. Extraer características de cada átomo → tensor x
      4. Extraer características de cada enlace → tensor edge_attr
      5. Construir edge_index (bidireccional: cada enlace genera 2 aristas)

    Args:
        smiles: cadena SMILES de la molécula
        labels: etiquetas de toxicidad (12 valores para Tox21)
        mask: máscara de mediciones válidas (True = medido, False = NaN)

    Returns:
        Data de PyG o None si el SMILES es inválido
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Canonicalizar para que el orden de átomos sea siempre el mismo
    smiles_canon = Chem.MolToSmiles(mol)
    mol = Chem.MolFromSmiles(smiles_canon)
    if mol is None:
        return None

    # Nodos: un vector de 45 features por cada átomo
    x = torch.tensor([atom_features(a) for a in mol.GetAtoms()], dtype=torch.float)

    # Aristas: bidireccionales (i→j y j→i para cada enlace)
    edge_index: list[list[int]] = []
    edge_attr: list[list[float]] = []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        feat = bond_features(bond)
        edge_index += [[i, j], [j, i]]
        edge_attr += [feat, feat]

    # Manejar moléculas sin enlaces (átomos aislados)
    if not edge_index:
        edge_index_t = torch.empty((2, 0), dtype=torch.long)
        edge_attr_t = torch.empty((0, EDGE_FEAT_DIM), dtype=torch.float)
    else:
        edge_index_t = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_attr_t = torch.tensor(edge_attr, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index_t, edge_attr=edge_attr_t)

    # Agregar etiquetas y máscara si se proporcionan.
    # Forma (1, n_tasks): PyG concatena por grafo → (batch_size, n_tasks).
    # Con forma (n_tasks,) el batch quedaría (batch_size * n_tasks,) y rompe la loss.
    if labels is not None:
        y = torch.tensor(labels, dtype=torch.float).view(1, -1)
        y = torch.nan_to_num(y, nan=0.0)
        data.y = y
    if mask is not None:
        data.mask = torch.tensor(mask, dtype=torch.bool).view(1, -1)
    return data
