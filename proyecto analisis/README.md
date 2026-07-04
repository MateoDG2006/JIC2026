# Proyecto Análisis de Datos — ChEMBL × Plaguicidas Panamá

Curso de análisis de datos sobre bioactividad ChEMBL de ingredientes activos del MIDA.
**Separado del proyecto GNN (JIC 2026)** en el monorepo `JIC2026/`.

## Estructura

```
proyecto analisis/
├── config/config.yaml       # ChEMBL + viz analytics
├── data/
│   ├── raw/                 # Extracción ChEMBL + geodatos
│   ├── processed/           # activities_clean + compounds_features (107)
│   └── external/chembl/     # chembl_37.db (SQLite local)
├── src/analisis_proyecto/   # Pipeline Python
├── notebooks/               # Fases 1–7 + anexo baseline
├── docs/                    # Documentación por fase
├── outputs/chembl/          # Figuras, modelos legacy, resultados
├── outputs/dashboard/       # JSON para viz analytics
├── scripts/                 # CLI por fase
├── docker/chembl-init/      # Descarga BD ChEMBL
└── viz/                     # FastAPI analytics (puerto 8001)
```

## Inicio rápido

```bash
cd "proyecto analisis"
pip install -r requirements.txt

# Verificación pipeline Opción A
python scripts/fase4/verify_flow_b.py

# Notebooks (orden)
jupyter notebook notebooks/fase2_limpieza.ipynb

# Visor analytics
python viz/app.py
```

## Unidad de análisis

**107 compuestos** (`compounds_features.csv`), no filas de medición.
El baseline predictivo está en `notebooks/anexo_baseline_predictivo.ipynb`.

## Proyecto hermano

El GNN-GIN + XAI vive en la raíz del monorepo (`src/models/gin.py`, `notebooks/04_gnn_training.ipynb`).
