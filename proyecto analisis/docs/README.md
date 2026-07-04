# Proyecto de Analisis de Datos — Perfilado y Caracterizacion de Bioactividad de Plaguicidas de Uso en Panama (ChEMBL)

Documentacion del modulo de **ciencia de datos clasica** anadido al repositorio JIC2026 para cumplir los requisitos del curso de Analisis de Datos y Toma de Decisiones, manteniendo coherencia tematica con el pipeline GNN + XAI del proyecto JIC.

**Naturaleza del estudio:** exploratorio + multivariado + inferencial sobre los 107 plaguicidas del corpus panameno en ChEMBL. El proyecto **NO tiene como producto principal un modelo predictivo** — el intento inicial de predecir toxicidad/potencia (clasificacion y regresion con RF/SVM sobre descriptores moleculares) fallo por diseno de datos, no por codigo: 107 compuestos unicos generan 3.608 mediciones/filas, y los descriptores moleculares son constantes dentro de cada compuesto, por lo que un split por fila filtra el mismo compuesto entre train y test (fuga de datos) y las metricas quedan infladas. Con split honesto por compuesto el modelo no generaliza.

**Tesis del reencuadre:** los 107 plaguicidas SI son caracterizables y agrupables por su perfil fisicoquimico y de bioactividad (EDA, clustering, contraste de hipotesis), pero los descriptores moleculares clasicos **no bastan para predecir potencia en compuestos no vistos** — este limite honesto motiva y justifica el enfoque de grafos moleculares (GNN) del proyecto JIC, que aprende representaciones directamente del grafo atomo-enlace en lugar de descriptores tabulares fijos.

La documentacion esta organizada por **fase del proyecto**. Cada fase describe objetivo, pipeline, decisiones tecnicas, trabajo por rol y criterios de exito.

---

## Indice de Fases

| # | Fase | Objetivo | Flujo |
|---|---|---|---|
| 1 | [Adquisicion y extraccion de datos](fases/fase1_adquisicion_datos.md) | Construir dataset tabular desde ChEMBL | Flujo A |
| 2 | [Limpieza e ingenieria de datos](fases/fase2_limpieza_datos.md) | Deduplicar, censurar y consolidar en dos tablas: medicion y compuesto | Flujo B (Secciones 0, 2) |
| 3 | [Analisis exploratorio (EDA)](fases/fase3_eda.md) | Describir distribucion fisicoquimica y de bioactividad a nivel compuesto (107) | Flujo B (Secciones 1, 3) |
| 4 | [Analisis multivariado y contraste de hipotesis](fases/fase4_modelado.md) | PCA + clustering (silhouette, ARI) + pruebas estadisticas (Kruskal-Wallis, Dunn, tamano de efecto) — SIN clasificacion/regresion como producto | Flujo B (Secciones 4, 5) |
| 5 | [Integracion y dashboard](fases/fase5_dashboard.md) | Explorador de compuestos (perfil fisicoquimico + dianas + cluster), no "predictor de toxicidad" | Flujo C |
| 6 | [Geodatos y contexto Panama](fases/fase6_geodatos.md) | **PARQUEADA** — pendiente dataset de uso/registro de plaguicidas por distrito | Flujo D |
| 7 | [Comunicacion de resultados](fases/fase7_comunicacion.md) | Articulo IEEE + video explicativo, narrativa de caracterizacion + limite que motiva el GNN | Flujo E |
| Anexo | [Baseline predictivo honesto](fases/anexo_baseline_predictivo.md) (adicional, separado) | Reportar el limite del split por compuesto (R² negativo) como puente honesto hacia el GNN de la JIC | Flujo B (documento propio) |

Referencia transversal: [Metricas de evaluacion](../../mateo_docs/auditorias/METRICAS_EVALUACION.md) — sigue vigente: explica la fuga de datos por split de filas y por que el R² negativo por compuesto es el resultado honesto, no un error.

---

## Resumen de Roles

| Rol | Responsabilidad principal | Fases donde lidera | Fases donde apoya |
|---|---|---|---|
| **Ingeniero de Datos** | Pipeline de datos, calidad, infraestructura | 1, 2 | 5 |
| **Analista de Datos** | EDA, visualizaciones, interpretacion | 3 | 4, 7 |
| **Cientifico de Datos** | Analisis multivariado, estadistica inferencial, baseline honesto | 4, Anexo | 3, 7 |
| **ML Engineer** | Despliegue, dashboard, integracion de resultados | 5 | 1, 2, 4, 7 |

Fase 6 (Geodatos) esta **parqueada**: no tiene rol lider activo hasta contar con un dataset real de uso/registro de plaguicidas por distrito. El codigo existente se conserva referenciado pero se retira del pipeline principal, del indice ejecutable y del articulo.

### Matriz de Responsabilidad (RACI)

| Fase | Ing. Datos | Analista | Cientifico | ML Engineer |
|---|---|---|---|---|
| 1. Adquisicion | **R** | I | I | A |
| 2. Limpieza | **R** | A | I | A |
| 3. EDA | I | **R** | A | I |
| 4. Analisis multivariado y contraste de hipotesis | I | A | **R** | A |
| Anexo. Baseline predictivo honesto | I | I | **R** | A |
| 5. Dashboard | A | A | I | **R** |
| 6. Geodatos | — PARQUEADA — | — | — | — |
| 7. Articulo IEEE | A | **R** | **R** | A |
| 7. Video | I | A | A | **R** |

**Leyenda:** R = Responsable (lidera), A = Apoya, I = Informado

---

## Archivos Clave por Fase

| Fase | Entrada | Salida principal | Codigo fuente |
|---|---|---|---|
| 1 | `pubchem_panama_cids.csv` | `chembl_panama_bioactivity.csv` | `src/analisis_proyecto/chembl_*.py` |
| 2 | `chembl_panama_bioactivity.csv` | `activities_clean.csv` (medicion, dedup) + `compounds_features.csv` (compuesto, 107 filas) | `chembl_preprocessing.py` |
| 3 | `compounds_features.csv` + `activities_clean.csv` | Figuras EDA a nivel compuesto (distribuciones, boxplots por familia) + correlacion | `chembl_preprocessing.py` |
| 4 | `compounds_features.csv` + `activities_clean.csv` | `stats_tests.csv` + `clustering_summary.json` + figuras (PCA, dendrograma, silhouette) | `chembl_preprocessing.py` |
| Anexo | `compounds_features.csv` | `baseline_honest_metrics.csv` | `chembl_preprocessing.py` |
| 5 | Todos los artefactos anteriores | Dashboard (explorador de compuestos) en `viz/` | `viz/routes/analytics.py` |
| 6 (parqueada) | geoBoundaries API + constantes INEC | `panama_geodata.csv` + GeoJSON (no integrado al pipeline activo) | `geodata_panama.py` |
| 7 | Todo lo anterior (excepto Fase 6) | Articulo PDF + Video MP4 | — |

---

## Codigo fuente

| Modulo | Rol |
|---|---|
| `src/analisis_proyecto/chembl_api.py` | Descarga y construccion del dataset (Flujo A, backend REST) |
| `src/analisis_proyecto/chembl_local.py` | Extraccion SQLite offline (Flujo A, backend SQLite) |
| `src/analisis_proyecto/chembl_extract.py` | Facade unificada de extraccion (Flujo A) |
| `src/analisis_proyecto/chembl_preprocessing.py` | Preprocesamiento, EDA, analisis multivariado y baseline honesto (Flujo B) |
| `src/analisis_proyecto/geodata_panama.py` | Geodatos Panama (Flujo D, parqueado) |
| `scripts/analisis_proyecto/fase1/extract_chembl_local.py` | CLI extraccion ChEMBL (Fase 1) |
| `scripts/analisis_proyecto/fase1/verify_chembl_db.py` | Diagnostico ChEMBLdb (Fase 1) |
| `scripts/analisis_proyecto/fase4/verify_flow_b.py` | Verificacion end-to-end Flujo B (Fase 4) |
| `scripts/analisis_proyecto/fase5/03_prepare_dashboard_data.py` | Shim al pipeline de dashboard (Fase 5) |
| `scripts/analisis_proyecto/fase5/test_dashboard.py` | Shim al smoke test del dashboard (Fase 5) |
| `scripts/analisis_proyecto/fase6/02_download_geodata.py` | CLI geodatos Panama (Fase 6, parqueado) |
| `scripts/fase5/prepare_dashboard.py` | Genera artefactos JSON para el dashboard |
| `viz/` | Aplicacion FastAPI unificada (GNN 3D + analytics) |

Funciones clave de `chembl_preprocessing.py` referenciadas en las fases: `filter_potential_duplicates`, `impute_median_by_family`, `train_test_split_by_group`, `evaluate_regression`, `correlation_with_target`, `plot_missingno_report`, `pchembl_imputation_report`, `drop_columns_high_nan`, `summary_statistics`. La funcion `build_compound_features(activities_df) -> pd.DataFrame` (nueva funcion — a implementar) consolida `activities_clean.csv` en `compounds_features.csv`.

---

## Notebooks

| Notebook | Fase | Rol |
|---|---|---|
| `notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb` | 1 | Extracción ChEMBL, mapeo MIDA, filtros de calidad |
| `notebooks/proyecto analisis de datos/fase2_limpieza.ipynb` | 2 | Diagnóstico NaN (missingno + UpSet), dedup, imputación por familia, construcción de `compounds_features.csv` |
| `notebooks/proyecto analisis de datos/fase3_eda.ipynb` | 3 | Tendencia central y distribuciones a nivel compuesto, promiscuidad, Pearson + Spearman |
| `notebooks/proyecto analisis de datos/fase4_modelado.ipynb` | 4 | PCA, clustering jerárquico/K-means, Kruskal-Wallis + post-hoc Dunn, tamaño de efecto |
| `notebooks/proyecto analisis de datos/anexo_baseline_predictivo.ipynb` | Anexo | Baseline honesto con split por compuesto — RF/SVM/SVR como límite, no como logro (nuevo notebook — a implementar) |
| `notebooks/proyecto analisis de datos/fase5_dashboard.ipynb` | 5 | Artefactos JSON + smoke test FastAPI |
| `notebooks/proyecto analisis de datos/fase6_geodatos.ipynb` | 6 | geoBoundaries + INEC, mapa coroplético (parqueado, no ejecutado en el pipeline activo) |
| `notebooks/proyecto analisis de datos/fase7_comunicacion.ipynb` | 7 | Tablas y figuras finales (artículo IEEE, video, slides) |

---

## Comandos Rapidos por Fase

```bash
# Fase 1 — Extraccion
make chembl-extract
jupyter notebook "notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb"

# Fases 2 + 3 + 4 — Flujo B (limpieza, EDA, analisis multivariado)
make test-chembl-flow-b
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Anexo — Baseline predictivo honesto (adicional, separado del analisis principal)
jupyter notebook "notebooks/proyecto analisis de datos/anexo_baseline_predictivo.ipynb"

# Fase 5 — Dashboard
make prepare-dashboard
make viz
# -> http://127.0.0.1:8000

# Fase 6 — Geodatos (PARQUEADA, no forma parte del pipeline activo)
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

# 2-4) Limpieza, EDA y analisis multivariado (notebook por fase)
make test-chembl-flow-b
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Anexo) Baseline predictivo honesto (adicional, separado, puente hacia el GNN de la JIC)
jupyter notebook "notebooks/proyecto analisis de datos/anexo_baseline_predictivo.ipynb"

# 5) Dashboard
make prepare-dashboard
make viz
jupyter notebook "notebooks/proyecto analisis de datos/fase5_dashboard.ipynb"

# 6) Geodatos — PARQUEADA, ejecutar solo si se retoma con dataset real de uso/registro por distrito
jupyter notebook "notebooks/proyecto analisis de datos/fase6_geodatos.ipynb"

# 7) Comunicacion (tablas + figuras para articulo)
jupyter notebook "notebooks/proyecto analisis de datos/fase7_comunicacion.ipynb"
```

---

## Plan maestro

[EXPANSION_CHEMBL_PLAN.md](../../mateo_docs/planes/EXPANSION_CHEMBL_PLAN.md)
