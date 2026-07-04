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
├── notebooks/               # Fases 1–7 (baseline P6 en fase4 + notebook dedicado)
├── docs/                    # Documentación por fase
├── outputs/chembl/          # Figuras, modelos legacy, resultados
├── outputs/dashboard/       # JSON para viz analytics
├── scripts/                 # CLI por fase
├── docker/chembl-init/      # Descarga BD ChEMBL
└── viz/                     # FastAPI analytics (puerto 8001)
```

## Inicio rápido

Todos los comandos se ejecutan desde la **raíz del monorepo** (`JIC2026/`):

```bash
make help              # listado de comandos JIC + analisis
make setup             # entorno JIC
make setup-analisis    # deps adicionales del subproyecto

# Analisis — pipeline
make chembl-extract
make analisis-verify
jupyter notebook "proyecto analisis/notebooks/fase2_limpieza.ipynb"

# Analisis — dashboard (puerto 8001)
make analisis-prepare-dashboard
make analisis-viz

# JIC — visor GNN (puerto 8000)
make setup-viz
make viz
```

## Unidad de análisis

**107 compuestos** (`compounds_features.csv`), no filas de medición.
El baseline predictivo honesto (P6) está en la **§4** de [`notebooks/fase4_modelado.ipynb`](notebooks/fase4_modelado.ipynb) y documentado en [Fase 4 §12](docs/fases/fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6).

## Proyecto hermano

El GNN-GIN + XAI vive en la raíz del monorepo (`src/models/gin.py`, `notebooks/04_gnn_training.ipynb`).
