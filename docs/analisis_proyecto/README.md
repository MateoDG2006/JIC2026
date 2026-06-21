# Proyecto de Analisis de Datos — ChEMBL x Plaguicidas Panama

Documentacion del modulo de **ciencia de datos clasica** anadido al repositorio JIC2026 para cumplir los requisitos del curso de Analisis de Datos y Toma de Decisiones, manteniendo coherencia tematica con el pipeline GNN + XAI del proyecto JIC.

La documentacion esta organizada por **fase del proyecto**. Cada fase describe objetivo, pipeline, decisiones tecnicas, trabajo por rol y criterios de exito.

---

## Indice de Fases

| # | Fase | Objetivo | Flujo |
|---|---|---|---|
| 1 | [Adquisicion y extraccion de datos](fases/fase1_adquisicion_datos.md) | Construir dataset tabular desde ChEMBL | Flujo A |
| 2 | [Limpieza e ingenieria de datos](fases/fase2_limpieza_datos.md) | Tratar faltantes, imputar, generar features | Flujo B (Secciones 0, 2) |
| 3 | [Analisis exploratorio (EDA)](fases/fase3_eda.md) | Describir distribucion, tendencia central, correlaciones | Flujo B (Secciones 1, 3) |
| 4 | [Modelado predictivo](fases/fase4_modelado.md) | Clasificacion y regresion con metricas | Flujo B (Secciones 4, 5) |
| 5 | [Integracion y dashboard](fases/fase5_dashboard.md) | Dashboard web interactivo (FastAPI + Plotly) | Flujo C |
| 6 | [Geodatos y contexto Panama](fases/fase6_geodatos.md) | Mapa coropletico con datos sociodemograficos | Flujo D |
| 7 | [Comunicacion de resultados](fases/fase7_comunicacion.md) | Articulo IEEE + video explicativo | Flujo E |

Referencia transversal: [Metricas de evaluacion](../../mateo_docs/auditorias/METRICAS_EVALUACION.md) — interpretacion de splits, accuracy inflada y R² negativo.

---

## Resumen de Roles

| Rol | Responsabilidad principal | Fases donde lidera | Fases donde apoya |
|---|---|---|---|
| **Ingeniero de Datos** | Pipeline de datos, calidad, infraestructura | 1, 2, 6 | 5 |
| **Analista de Datos** | EDA, visualizaciones, interpretacion | 3 | 6, 7 |
| **Cientifico de Datos** | Modelos, metricas, validacion estadistica | 4 | 3, 7 |
| **ML Engineer** | Despliegue, dashboard, integracion de modelos | 5 | 1, 2, 4, 7 |

### Matriz de Responsabilidad (RACI)

| Fase | Ing. Datos | Analista | Cientifico | ML Engineer |
|---|---|---|---|---|
| 1. Adquisicion | **R** | I | I | A |
| 2. Limpieza | **R** | A | I | A |
| 3. EDA | I | **R** | A | I |
| 4. Modelado | I | A | **R** | A |
| 5. Dashboard | A | A | I | **R** |
| 6. Geodatos | **R** | A | I | A |
| 7. Articulo IEEE | A | **R** | **R** | A |
| 7. Video | I | A | A | **R** |

**Leyenda:** R = Responsable (lidera), A = Apoya, I = Informado

---

## Archivos Clave por Fase

| Fase | Entrada | Salida principal | Codigo fuente |
|---|---|---|---|
| 1 | `pubchem_panama_cids.csv` | `chembl_panama_bioactivity.csv` | `src/analisis_proyecto/chembl_*.py` |
| 2 | `chembl_panama_bioactivity.csv` | `chembl_clean.csv` | `chembl_preprocessing.py` |
| 3 | `chembl_clean.csv` | Figuras PNG + JSON correlacion | `chembl_preprocessing.py` |
| 4 | `chembl_clean.csv` | Modelos `.pkl` + `metrics_summary.csv` | `chembl_preprocessing.py` |
| 5 | Todos los artefactos anteriores | Dashboard en `viz/` | `viz/routes/analytics.py` |
| 6 | geoBoundaries API + constantes INEC | `panama_geodata.csv` + GeoJSON | `geodata_panama.py` |
| 7 | Todo lo anterior | Articulo PDF + Video MP4 | — |

---

## Codigo fuente

| Modulo | Rol |
|---|---|
| `src/analisis_proyecto/chembl_api.py` | Descarga y construccion del dataset (Flujo A, backend REST) |
| `src/analisis_proyecto/chembl_local.py` | Extraccion SQLite offline (Flujo A, backend SQLite) |
| `src/analisis_proyecto/chembl_extract.py` | Facade unificada de extraccion (Flujo A) |
| `src/analisis_proyecto/chembl_preprocessing.py` | Preprocesamiento y utilidades EDA + modelado (Flujo B) |
| `src/analisis_proyecto/geodata_panama.py` | Geodatos Panama (Flujo D) |
| `scripts/analisis_proyecto/fase1/extract_chembl_local.py` | CLI extraccion ChEMBL (Fase 1) |
| `scripts/analisis_proyecto/fase1/verify_chembl_db.py` | Diagnostico ChEMBLdb (Fase 1) |
| `scripts/analisis_proyecto/fase4/verify_flow_b.py` | Verificacion end-to-end Flujo B (Fase 4) |
| `scripts/analisis_proyecto/fase5/03_prepare_dashboard_data.py` | Shim al pipeline de dashboard (Fase 5) |
| `scripts/analisis_proyecto/fase5/test_dashboard.py` | Shim al smoke test del dashboard (Fase 5) |
| `scripts/analisis_proyecto/fase6/02_download_geodata.py` | CLI geodatos Panama (Fase 6) |
| `scripts/fase5/prepare_dashboard.py` | Genera artefactos JSON para el dashboard |
| `viz/` | Aplicacion FastAPI unificada (GNN 3D + analytics) |

---

## Notebooks

| Notebook | Fase | Rol |
|---|---|---|
| `notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb` | 1 | Extracción ChEMBL, mapeo MIDA, filtros de calidad |
| `notebooks/proyecto analisis de datos/fase2_limpieza.ipynb` | 2 | Diagnóstico NaN (missingno + UpSet), imputación por familia |
| `notebooks/proyecto analisis de datos/fase3_eda.ipynb` | 3 | Tendencia central, distribuciones, Pearson + Spearman |
| `notebooks/proyecto analisis de datos/fase4_modelado.ipynb` | 4 | RF/SVM (clf) + RF/SVR (reg), split filas vs compuesto |
| `notebooks/proyecto analisis de datos/fase5_dashboard.ipynb` | 5 | Artefactos JSON + smoke test FastAPI |
| `notebooks/proyecto analisis de datos/fase6_geodatos.ipynb` | 6 | geoBoundaries + INEC, mapa coroplético |
| `notebooks/proyecto analisis de datos/fase7_comunicacion.ipynb` | 7 | Tablas y figuras finales (artículo IEEE, video, slides) |

---

## Comandos Rapidos por Fase

```bash
# Fase 1 — Extraccion
make chembl-extract
jupyter notebook "notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb"

# Fases 2 + 3 + 4 — Flujo B (limpieza, EDA, modelado)
make test-chembl-flow-b
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Fase 5 — Dashboard
make prepare-dashboard
make viz
# -> http://127.0.0.1:8000

# Fase 6 — Geodatos
make download-geodata

# Pipelines combinados
make viz-analytics-all    # geodata + prepare-dashboard + test
make viz-jic              # panama-predict + prepare-dashboard + test
```

---

## Ejecucion completa desde cero

```bash
cd JIC2026
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1) Extraccion ChEMBL
make chembl-extract
jupyter notebook "notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb"

# 2-4) Analisis y modelado (notebook por fase)
make test-chembl-flow-b
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# 5) Dashboard
make prepare-dashboard
make viz
jupyter notebook "notebooks/proyecto analisis de datos/fase5_dashboard.ipynb"

# 6) Geodatos
jupyter notebook "notebooks/proyecto analisis de datos/fase6_geodatos.ipynb"

# 7) Comunicacion (tablas + figuras para articulo)
jupyter notebook "notebooks/proyecto analisis de datos/fase7_comunicacion.ipynb"
```

---

## Plan maestro

[EXPANSION_CHEMBL_PLAN.md](../../mateo_docs/planes/EXPANSION_CHEMBL_PLAN.md)
