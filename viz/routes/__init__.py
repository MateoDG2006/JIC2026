"""Routers FastAPI del visor GNN-Tox.

Cada submódulo expone un ``APIRouter`` que se monta en ``viz.app``:

    views     → vistas HTML del visor 3D (index, molecule, analyze)
    api       → API REST para predicción/XAI sobre SMILES arbitrarios (/api/...)
    analytics → API + HTML para EDA, modelos ChEMBL y mapa Panamá
"""
