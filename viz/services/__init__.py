"""Servicios reutilizables del visor GNN-Tox.

Aislan la lógica de negocio (modelo, química, persistencia) de las
rutas HTTP, lo que permite testear cada pieza por separado.

Módulos:
    inference   — singleton del modelo GIN + predict + GNNExplainer/Grad-CAM
    molecule    — utilidades RDKit (SMILES → SDF/MOL, propiedades, símbolos)
    corpus      — corpus precomputado (lectura JSON desde viz/data/)
    dashboard/  — artefactos para analytics: ChEMBL, geo, modelos, caché checksum
"""
