"""Visor web GNN-Tox unificado (FastAPI + Plotly.js + 3Dmol).

Empaqueta en una sola aplicación FastAPI:

  - Visor 3D del modelo GIN sobre moléculas individuales (``/``, ``/molecule/``,
    ``/analyze``) — predicción Tox21 + XAI overlay sobre estructura 3D.
  - Analytics ChEMBL / Panamá (``/eda``, ``/chembl/models``, ``/panama/*``)
    para la parte de "analítica de datos" del curso.
  - APIs REST (``/api/...``) para predicción, XAI, propiedades y corpus.
  - Health check (``/health``) y refresh de caché (``POST /api/analytics/refresh``).

Submódulos:
    app             — entry point FastAPI; monta static y routers
    config          — paths del proyecto, TASK_NAMES locales, viz host/port
    routes/views    — vistas HTML del visor 3D (index, molecule, analyze)
    routes/api      — JSON API: /predict, /explain, /analyze, /mol3d
    routes/analytics — JSON+HTML de EDA, modelos ChEMBL, mapa Panamá
    services/inference — carga del modelo GIN + predict + GNNExplainer/GradCAM
    services/molecule  — utilidades RDKit (SMILES → SDF, propiedades)
    services/corpus    — listado y carga del corpus precomputado
    services/dashboard — artefactos JSON/CSV con caché por checksum (P3)
"""
