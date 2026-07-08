# Proyecto de Analisis de Datos — Perfilado y Caracterizacion de Bioactividad de Plaguicidas de Uso en Panama (ChEMBL)

Documentacion del modulo de **ciencia de datos clasica** anadido al repositorio JIC2026 para cumplir los requisitos del curso de Analisis de Datos y Toma de Decisiones, manteniendo coherencia tematica con el pipeline GNN + XAI del proyecto JIC.

**Naturaleza del estudio:** exploratorio + multivariado + inferencial sobre los **151 compuestos estructurales** (94 con potencia util) del corpus panameno en ChEMBL. El proyecto **NO tiene como producto principal un modelo predictivo** — el intento inicial de predecir toxicidad/potencia (clasificacion y regresion con RF/SVM sobre descriptores moleculares) fallo por diseno de datos, no por codigo: 151 compuestos unicos generan 10.095 mediciones/filas, y los descriptores moleculares son constantes dentro de cada compuesto, por lo que un split por fila filtra el mismo compuesto entre train y test (fuga de datos) y las metricas quedan infladas. Con split honesto por compuesto el modelo no generaliza (R2 negativo).

> **Nota (jul-2026):** los numeros se actualizaron a 151/94/10.095 tras corregir el registro MIDA (11 de 20 ChEMBL IDs apuntaban a la molecula equivocada; verificados por InChIKey y re-extraidos). Los docs de fase individuales aun pueden citar cifras viejas (107/3.608 o 147/89/9.752) — la fuente canonica son los artefactos regenerados en `data/processed/` y `outputs/chembl/results/`.

**Tesis del reencuadre:** los 151 plaguicidas SI son caracterizables y agrupables por su perfil fisicoquimico y de bioactividad (EDA, clustering, contraste de hipotesis), pero los descriptores moleculares clasicos **no bastan para predecir potencia en compuestos no vistos** — este limite honesto se cuantifica en la **Fase 4 (P6, §12)** y motiva el enfoque de grafos moleculares (GNN) del proyecto JIC.

La documentacion esta organizada por **fase del proyecto**. Cada fase describe objetivo, pipeline, decisiones tecnicas, trabajo por rol y criterios de exito.

---

## Indice de Fases

| # | Fase | Objetivo | Flujo |
|---|---|---|---|
| 1 | [Adquisicion y extraccion de datos](fases/fase1_adquisicion_datos.md) | Construir dataset tabular desde ChEMBL; documentar limite n=94 (potencia) | Flujo A |
| 2 | [Limpieza e ingenieria de datos](fases/fase2_limpieza_datos.md) | Deduplicar, censurar y consolidar en dos tablas: medicion y compuesto | Flujo B (Secciones 0, 2) |
| 3 | [Analisis exploratorio (EDA)](fases/fase3_eda.md) | Describir distribucion fisicoquimica y de bioactividad a nivel compuesto (151) | Flujo B (Secciones 1, 3) |
| 4 | [Analisis multivariado, contraste de hipotesis y baseline P6](fases/fase4_modelado.md) | PCA + clustering + Kruskal/Dunn **y** baseline predictivo honesto (limite descriptores → puente GNN) | Flujo B (Secciones 4, 5, 12) |
| 5 | [Integracion y dashboard](fases/fase5_dashboard.md) | Explorador de compuestos (perfil + cluster), sin predictor roto | Flujo C |
| 6 | [Geodatos y contexto Panama](fases/fase6_geodatos.md) | **Spec futura** — mapa coropletico cuando exista dataset MIDA/INEC | Flujo D |
| 7 | [Comunicacion de resultados](fases/fase7_comunicacion.md) | Articulo IEEE + video: caracterizacion + limite P6 que motiva el GNN | Flujo E |

Referencia transversal: [Metricas de evaluacion](../../mateo_docs/auditorias/METRICAS_EVALUACION.md) — explica la fuga por split de filas y por que el R² negativo por compuesto es el resultado honesto.

---

## Resumen de Roles

| Rol | Responsabilidad principal | Fases donde lidera | Fases donde apoya |
|---|---|---|---|
| **Ingeniero de Datos** | Pipeline de datos, calidad, infraestructura | 1, 2 | 5 |
| **Analista de Datos** | EDA, visualizaciones, interpretacion | 3 | 4, 7 |
| **Cientifico de Datos** | Multivariado, inferencia, baseline honesto (P6) | 4 | 3, 7 |
| **ML Engineer** | Dashboard, integracion (sin desplegar predictor P6) | 5 | 1, 2, 4, 7 |

Fase 6 (Geodatos) **no esta implementada**: solo [spec futura](fases/fase6_geodatos.md).

### Matriz de Responsabilidad (RACI)

| Fase | Ing. Datos | Analista | Cientifico | ML Engineer |
|---|---|---|---|---|
| 1. Adquisicion | **R** | I | I | A |
| 2. Limpieza | **R** | A | I | A |
| 3. EDA | I | **R** | A | I |
| 4. Multivariado + baseline P6 | I | A | **R** | A |
| 5. Dashboard | A | A | I | **R** |
| 6. Geodatos | — PARQUEADA — | — | — | — |
| 7. Articulo IEEE | A | **R** | **R** | A |
| 7. Video | I | A | A | **R** |

**Leyenda:** R = Responsable (lidera), A = Apoya, I = Informado

---

## Archivos Clave por Fase

| Fase | Entrada | Salida principal | Codigo fuente |
|---|---|---|---|
| 1 | `pubchem_panama_cids.csv` | `chembl_panama_bioactivity.csv` | `chembl_*.py` |
| 2 | `chembl_panama_bioactivity.csv` | `activities_clean.csv` + `compounds_all.csv` (151) + `compounds_features.csv` (94) | `preprocessing/pipeline.py` |
| 3 | `compounds_features.csv` + `activities_clean.csv` | Figuras EDA | `preprocessing/pipeline.py` |
| 4 | `compounds_features.csv` | `stats_tests.csv`, `clustering_summary.json`, `baseline_honest_metrics.csv`, figuras PCA/cluster | `modeling/multivariate.py`, `modeling/baseline.py` |
| 5 | Artefactos Fases 2–4 | Dashboard en `viz/` (puerto 8001) | `prepare_dashboard.py`, `viz/` |
| 6 | — spec futura — | GeoJSON (futuro) | ver [fase6_geodatos.md](fases/fase6_geodatos.md) |
| 7 | Artefactos Fases 2–5 + `baseline_honest_metrics.csv` | Articulo + video | — |

---

## Codigo fuente

| Modulo | Rol |
|---|---|
| `config/chembl/*.json` | Constantes editables (MIDA, columnas, tipos de actividad, esquema SQLite) |
| `src/analisis_proyecto/core/constants.py` | Carga de JSON en `config/chembl/` |
| `src/analisis_proyecto/core/models.py` | Dataclasses tipadas (`ChemblConfig`, `MidaRegistry`, …) |
| `src/analisis_proyecto/acquisition/extract.py` | Orquestador `ChemblExtractor` (Flujo A) |
| `src/analisis_proyecto/acquisition/remote.py` | Cliente HTTP hacia chembl-server |
| `src/analisis_proyecto/acquisition/server.py` | API FastAPI (solo contenedor Docker) |
| `src/analisis_proyecto/acquisition/local.py` | Consultas SQLite internas del servidor |
| `src/analisis_proyecto/acquisition/sqlalchemy.py` | SQLAlchemy Core — reflexion parcial (7 tablas) |
| `src/analisis_proyecto/acquisition/common.py` | Corpus, filtros de calidad, imputacion pChEMBL |
| `src/analisis_proyecto/preprocessing/pipeline.py` | Limpieza, EDA, features compuesto |
| `src/analisis_proyecto/modeling/multivariate.py` | PCA, clustering, Kruskal |
| `src/analisis_proyecto/modeling/baseline.py` | Baseline honesto P6 (`CompoundLevelBaseline`, `RowLevelLeakyBaseline`) |
| `scripts/fase1/extract_chembl.py` | CLI de extraccion ChEMBL |
| `scripts/fase4/verify_flow_b.py` | Verificacion end-to-end Flujo B |
| `scripts/fase5/prepare_dashboard.py` | JSON para dashboard |
| `viz/` | Dashboard analytics (puerto 8001) |

---

## Notebooks

| Notebook | Fase | Rol |
|---|---|---|
| `notebooks/fase1_adquisicion.ipynb` | 1 | Extraccion ChEMBL |
| `notebooks/fase2_limpieza.ipynb` | 2 | Limpieza, `compounds_features.csv` |
| `notebooks/fase3_eda.ipynb` | 3 | EDA a nivel compuesto |
| `notebooks/fase4_modelado.ipynb` | 4 | PCA, clustering, tests, baseline P6 (§4) |
| `notebooks/fase5_dashboard.ipynb` | 5 | Artefactos + smoke test |
| `notebooks/fase7_comunicacion.ipynb` | 7 | Tablas y figuras finales |

---

## Comandos Rapidos

```bash
# Fase 1
make chembl-extract

# Fases 2–4 (incluye baseline P6 en verify)
make analisis-verify
jupyter notebook "proyecto analisis/notebooks/fase2_limpieza.ipynb"
jupyter notebook "proyecto analisis/notebooks/fase3_eda.ipynb"
jupyter notebook "proyecto analisis/notebooks/fase4_modelado.ipynb"

# Fase 5
make analisis-prepare-dashboard
make analisis-viz    # http://127.0.0.1:8001
```

---

## Plan maestro

[EXPANSION_CHEMBL_PLAN.md](../../mateo_docs/planes/EXPANSION_CHEMBL_PLAN.md)
