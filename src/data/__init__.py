"""Carga de datos, featurización y datasets Tox21 / corpus Panamá.

Submódulos:
    featurizer       — SMILES → grafo PyG (45 features de átomo, 9 de enlace)
    dataset          — ToxicityDataset y constantes TASK_NAMES (12 dianas Tox21)
    splitter         — scaffold split de Murcko para evaluación honesta
    tox21_deepchem   — carga Tox21 vía DeepChem con caché local
    pubchem_api      — clientes REST de PubChem (Compound, BioAssay, GHS)

Los exports se cargan de forma perezosa (lazy) para evitar importar torch
cuando solo se necesita el cliente PubChem, etc.
"""

# Imports perezosos: evita cargar torch al importar submódulos ligeros.

_LAZY_EXPORTS = {
    "TASK_NAMES": ("src.data.dataset", "TASK_NAMES"),
    "ToxicityDataset": ("src.data.dataset", "ToxicityDataset"),
    "EDGE_FEAT_DIM": ("src.data.featurizer", "EDGE_FEAT_DIM"),
    "NODE_FEAT_DIM": ("src.data.featurizer", "NODE_FEAT_DIM"),
    "smiles_to_graph": ("src.data.featurizer", "smiles_to_graph"),
    "scaffold_split": ("src.data.splitter", "scaffold_split"),
    "save_split_indices": ("src.data.splitter", "save_split_indices"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = _LAZY_EXPORTS[name]
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr)
