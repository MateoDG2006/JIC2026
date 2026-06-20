# Proyecto de Análisis de Datos — ChEMBL × Plaguicidas Panamá

Documentación del módulo de **ciencia de datos clásica** añadido al repositorio JIC2026 para cumplir los requisitos del curso, manteniendo coherencia temática con el pipeline GNN + XAI.

## Etapas

| Doc | Notebook / App | Entrada | Salida principal |
|---|---|---|---|
| [00 — Extracción ChEMBL](00_extraccion_chembl.md) | `notebooks/proyecto analisis de datos/00_chembl_extraccion.ipynb` | `pubchem_panama_cids.csv` | `chembl_panama_bioactivity.csv` |
| [01 — Análisis de datos](01_analisis_datos_chembl.md) | `notebooks/proyecto analisis de datos/01_chembl_analisis_datos.ipynb` | `chembl_panama_bioactivity.csv` | `chembl_clean.csv` + modelos `.pkl` |
| [02 — Dashboard Dash](02_dashboard_dash.md) | `dashboard/app.py` | `chembl_clean.csv` + modelos + geojson | Dashboard web interactivo |

## Código fuente

| Módulo | Rol |
|---|---|
| `src/analisis_proyecto/chembl_api.py` | Descarga y construcción del dataset (Flujo A) |
| `src/analisis_proyecto/chembl_local.py` | Extracción SQLite offline (Flujo A) |
| `src/analisis_proyecto/chembl_extract.py` | Facade unificada extracción (Flujo A) |
| `src/analisis_proyecto/chembl_preprocessing.py` | Preprocesamiento y utilidades EDA (Flujo B) |
| `src/analisis_proyecto/geodata_panama.py` | Geodatos Panamá (Flujo D) |
| `scripts/analisis_proyecto/02_download_geodata.py` | CLI geodatos |
| `scripts/analisis_proyecto/03_prepare_dashboard_data.py` | Empaqueta artefactos dashboard |
| `scripts/analisis_proyecto/test_dashboard.py` | Smoke test Flujo C |
| `dashboard/` | Aplicación Dash-Plotly (Flujo C) |

## Plan maestro

[EXPANSION_CHEMBL_PLAN.md](../EXPANSION_CHEMBL_PLAN.md) — Flujo E (Artículo IEEE) pendiente.

## Ejecución rápida

```bash
cd JIC2026
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Etapa 00 — extracción ChEMBL
make chembl-extract

# Etapa 01 — análisis de datos
make test-chembl-flow-b
jupyter notebook "notebooks/proyecto analisis de datos/01_chembl_analisis_datos.ipynb"

# Etapa 02 — dashboard Dash
make dashboard-all
make dashboard-serve
# → http://127.0.0.1:8050
```
