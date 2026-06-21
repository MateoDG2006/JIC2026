# Predicción de Toxicidad de Agroquímicos — GNN-GIN, XAI y Analítica ChEMBL

Repositorio con **dos líneas de trabajo** complementarias sobre toxicidad de plaguicidas usados en Panamá:

1. **JIC 2026 — Sistema GNN-GIN + XAI sobre Tox21.** Química computacional que modela moléculas como **grafos** (átomos = nodos, enlaces = aristas), entrena una **GNN tipo GIN** sobre el benchmark **Tox21** (12 tareas de toxicidad) e incorpora **explicabilidad** (GNNExplainer, Grad-CAM) para identificar qué grupos funcionales causan la toxicidad predicha.
2. **Proyecto Análisis de Datos — ChEMBL × Plaguicidas Panamá.** Módulo de ciencia de datos clásica (Pandas, scikit-learn, missingno) sobre bioactividad ChEMBL de los ingredientes activos registrados por el MIDA, con extracción local SQLite + API REST, EDA, modelado RF/SVM/SVR y geodatos de distritos del país.

Ambas líneas comparten un **visor web** unificado (FastAPI + Plotly.js + 3Dmol.js) que sirve el visor 3D de moléculas con XAI integrado y el dashboard de analítica ChEMBL/Panamá.

---

## Estructura del repositorio

```
JIC2026/
├── config/
│   └── config.yaml                       # Hiperparámetros del modelo y entrenamiento
│
├── src/                                  # Código fuente compartido
│   ├── data/
│   │   ├── featurizer.py                 # SMILES → grafo PyG (45 feat. átomo, 9 feat. enlace)
│   │   ├── dataset.py                    # ToxicityDataset + TASK_NAMES (12 tareas Tox21)
│   │   ├── splitter.py                   # Scaffold split de Murcko
│   │   ├── tox21_deepchem.py             # Carga Tox21 desde DeepChem
│   │   └── pubchem_api.py                # Cliente PubChem (BioAssay, Compound, GHS)
│   ├── models/
│   │   ├── gin.py                        # GNN-GIN (GINEConv + residual + multitarea)
│   │   └── baselines.py                  # RF, MLP, SMILES2vec
│   ├── training/
│   │   ├── trainer.py                    # Loop con early stopping y CV scaffold
│   │   ├── loss.py                       # MaskedBCELoss (ignora NaN + pos_weight)
│   │   ├── schedulers.py                 # Cosine+warmup o ReduceLROnPlateau
│   │   ├── checkpoint.py                 # Selección del mejor modelo
│   │   └── metrics.py                    # Re-exporta métricas de evaluación
│   ├── xai/
│   │   ├── gnn_explainer.py              # GNNExplainer con _SingleTaskWrapper
│   │   ├── grad_cam.py                   # Grad-CAM adaptado a grafos
│   │   └── visualizer.py                 # SVG + colores hex YlOrRd (2D y 3D)
│   ├── evaluation/
│   │   ├── cross_validation.py           # AUC-ROC/AUPRC multitarea + folds scaffold
│   │   └── chemical_coherence.py         # Validación XAI con patrones SMARTS
│   └── analisis_proyecto/                # Módulo "Análisis de Datos" (Parte 2)
│       ├── chembl_api.py                 # Cliente ChEMBL REST (Flujo A)
│       ├── chembl_local.py               # Extracción ChEMBL SQLite offline (Flujo A)
│       ├── chembl_extract.py             # Fachada unificada de extracción
│       ├── chembl_preprocessing.py       # EDA, missingno, imputación, splits (Flujo B)
│       └── geodata_panama.py             # GeoJSON distritos + INEC (Flujo D)
│
├── viz/                                  # Visor web FastAPI (común a las 2 partes)
│   ├── app.py                            # Aplicación FastAPI
│   ├── config.py                         # Rutas, TASK_NAMES, host/port
│   ├── routes/
│   │   ├── views.py                      # Visor 3D (HTML)
│   │   ├── api.py                        # REST GNN: predict/explain/mol3d/svg
│   │   └── analytics.py                  # ChEMBL EDA + modelos + mapa Panamá
│   ├── services/
│   │   ├── inference.py                  # Modelo GIN cargado en memoria
│   │   ├── molecule.py                   # SMILES → SDF 3D, propiedades RDKit
│   │   ├── corpus.py                     # Corpus precomputado (viz/data/*.json)
│   │   └── dashboard/                    # Loaders ChEMBL/geo/XAI + caché checksum
│   ├── templates/                        # Jinja2: visor 3D + analytics_*.html
│   ├── static/                           # CSS, JS (3Dmol.js, Plotly.js)
│   └── data/                             # Corpus JSON precomputado
│
├── scripts/                              # Pipelines CLI
│   ├── fase1/                            # Tox21 → grafos
│   ├── fase2/                            # Baselines (RF, MLP, SMILES2vec)
│   ├── fase3/                            # Entrenamiento GIN + 5-fold CV
│   ├── fase4/                            # Visor (build_viz_corpus, viz_serve)
│   ├── fase5/                            # Corpus Panamá, XAI, reportes, dashboard prep
│   └── analisis_proyecto/                # Parte 2 — organizado por fase
│       ├── fase1/                        # Adquisición ChEMBL (extract, verify_db)
│       ├── fase4/                        # Verificación end-to-end Flujo B
│       ├── fase5/                        # Shims al dashboard (Fase 5)
│       └── fase6/                        # Geodatos Panamá
│
├── notebooks/
│   ├── 01_eda_tox21.ipynb                # EDA Tox21
│   ├── 02_baselines_tox21.ipynb          # Baselines
│   ├── 04_gnn_training.ipynb             # Entrenamiento GIN
│   ├── 06_panama_application.ipynb       # Aplicación a plaguicidas panameños
│   ├── 07_ghs_validation.ipynb           # Validación predicciones vs GHS
│   └── proyecto analisis de datos/       # Notebooks Parte 2
│       ├── fase1_adquisicion.ipynb       # Extracción + auditoría MIDA
│       ├── fase2_limpieza.ipynb          # Faltantes + imputación
│       ├── fase3_eda.ipynb               # EDA, correlaciones, distribuciones
│       ├── fase4_modelado.ipynb          # RF/SVM clf + RF/SVR reg
│       ├── fase5_dashboard.ipynb         # Artefactos JSON + smoke test FastAPI
│       ├── fase6_geodatos.ipynb          # geoBoundaries + INEC + mapa
│       ├── fase7_comunicacion.ipynb      # Tablas + figuras finales (IEEE)
│
├── docs/
│   ├── fase1_pipeline_datos.md           # Documentación Parte 1 (JIC)
│   ├── fase2_baselines.md
│   ├── fase3_modelo_gin.md
│   ├── fase4_xai.md
│   ├── fase5_panama.md
│   └── analisis_proyecto/                # Documentación Parte 2
│       ├── README.md                     # Índice, RACI, comandos por fase
│       └── fases/                        # 7 fases con rol líder
│
├── mateo_docs/                            # Documentación interna / personal (Mateo)
│   ├── auditorias/                        # Auditoría del proyecto y referencias de métricas
│   │   ├── AUDIT_REPORT.md
│   │   └── METRICAS_EVALUACION.md
│   └── planes/                            # Planes y hojas de ruta
│       └── EXPANSION_CHEMBL_PLAN.md
│
├── tests/                                # pytest: loss, splitter, cross_validation
├── data/                                 # Datos crudos y procesados (no en git)
├── outputs/                              # Modelos, resultados, gráficos (no en git)
├── Makefile                              # Comandos de pipeline
├── CLAUDE.md                             # Planificación detallada del proyecto
└── README.md                             # Este archivo
```

---

## Setup común

### 1. Dependencias

```bash
# Crear entorno (Python 3.10–3.12; deepchem no soporta 3.13+)
conda create -n toxgnn python=3.10
conda activate toxgnn
conda install -c conda-forge rdkit

# PyTorch con soporte GPU (CUDA 12.4)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# PyTorch Geometric (ajusta la URL si usas otra versión CUDA)
pip install torch_geometric torch_scatter torch_sparse torch_cluster \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html

pip install -r requirements.txt
```

Alternativa con Makefile (venv local en `.venv/`):

```bash
make setup
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
make install-pyg-ext
```

Verificar GPU:

```bash
make check-gin-gpu
# o: python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### 2. Tests

```bash
pytest
```

---

# Parte 1 — JIC 2026 · GNN-GIN + XAI sobre Tox21

Sistema de química computacional con explicabilidad orientado a evaluar el perfil toxicológico de plaguicidas registrados en el MIDA de Panamá.

## Idea central

| Aspecto | Detalle |
|---|---|
| **Problema** | Evaluar el perfil de toxicidad multitarea de plaguicidas sin depender solo de ensayos costosos |
| **Enfoque** | Grafo molecular + GIN (mensajes agregados con suma) + readout mean+max + cabeza multitarea (12 salidas) |
| **Datos** | Tox21 vía DeepChem (~8000 moléculas, 12 ensayos biológicos, datos faltantes con `MaskedBCELoss`) |
| **Split** | Scaffold de Murcko (sin filtración entre train/test) |
| **Baselines** | Random Forest, MLP, SMILES2vec — misma evaluación para comparación justa |
| **XAI** | GNNExplainer + Grad-CAM; colores YlOrRd unificados en SVG 2D y modelo 3D |
| **Visor web** | Dashboard FastAPI con corpus panameño, inferencia en vivo y visualización 3D/2D |
| **Objetivo** | AUC-ROC medio > 0.82 en test con scaffold split |

**Hipótesis:** Una GNN-GIN entrenada en grafos Tox21 predice el perfil de toxicidad de plaguicidas panameños con AUC-ROC superior a modelos QSAR clásicos, y las explicaciones XAI identifican grupos funcionales coherentes con mecanismos documentados.

## Las 5 fases

```mermaid
flowchart LR
    F1["Fase I<br/>Datos Tox21 + PubChem"]
    F2["Fase II<br/>Baselines"]
    F3["Fase III<br/>GNN-GIN"]
    F4["Fase IV<br/>XAI + visor"]
    F5["Fase V<br/>Panamá + GHS"]
    F1 --> F2 --> F3 --> F4 --> F5
```

| Fase | Descripción | Documentación |
|---|---|---|
| I | Pipeline de datos: SMILES → grafos, scaffold split, corpus panameño | [docs/fase1_pipeline_datos.md](docs/fase1_pipeline_datos.md) |
| II | Baselines: RF, MLP, SMILES2vec como referencia | [docs/fase2_baselines.md](docs/fase2_baselines.md) |
| III | Modelo GNN-GIN: arquitectura, entrenamiento, evaluación | [docs/fase3_modelo_gin.md](docs/fase3_modelo_gin.md) |
| IV | XAI: GNNExplainer, Grad-CAM, validación química, visor web | [docs/fase4_xai.md](docs/fase4_xai.md) |
| V | Aplicación a plaguicidas de Panamá, reportes MIDA/MINSA | [docs/fase5_panama.md](docs/fase5_panama.md) |

## Pipeline de entrenamiento

### 1. Preparar grafos Tox21

```bash
make prepare-graphs
# = python scripts/fase1/prepare_tox21_graphs.py
```

Genera `data/processed/graphs_{train,val,test}.pt` a partir de Tox21 (DeepChem).

### 2. Entrenar baselines (Fase II)

```bash
make train-baselines
make train-baselines-verbose    # modo verbose
```

Resultados en `outputs/results/baseline_results.csv` y gráficos en `outputs/baselines/`.

### 3. Entrenar GNN-GIN (Fase III)

```bash
make train-gin                  # entrenamiento estándar
make train-gin-verbose          # logs detallados
make train-gin-wandb            # logging con Weights & Biases
make train-gin-all              # prepare-graphs + train-gin
make train-gin-cv               # 5-fold cross-validation scaffold (AUDIT E2)
```

Guarda el mejor modelo en `outputs/models/best_gin_model.pt` y métricas en `outputs/results/gin_results.csv`.

### 4. Análisis exploratorio

```bash
make eda
# o abrir notebooks/01_eda_tox21.ipynb y notebooks/02_baselines_tox21.ipynb
```

### 5. Aplicación a Panamá (Fase V)

Requiere modelo entrenado (`make train-gin`) y corpus PubChem:

```mermaid
flowchart LR
    A["build-panama-corpus"] --> B["explain-panama"]
    B --> C["validate-ghs"]
    C --> D["generate-panama-report"]
```

```bash
make panama-all
```

Opciones útiles:

```bash
make build-panama-corpus-fast                            # sin descarga GHS
python scripts/fase5/explain_panama.py --skip-xai        # solo predicciones
python scripts/fase5/explain_panama.py --xai-mida-only   # XAI solo en 20 MIDA
```

Si un compuesto del corpus tiene SMILES atómico o GNNExplainer falla, el pipeline imprime `[WARN]`/`[SKIP]` y sigue con los demás (no detiene `make explain-panama`). Documentación de extracción PubChem y validación GHS en [docs/fase5_panama.md](docs/fase5_panama.md).

## Configuración (`config/config.yaml`)

| Parámetro | Default | Descripción |
|---|---|---|
| `model.hidden_dim` | 128 | Dimensión oculta de las capas GIN |
| `model.n_layers` | 3 | Capas de message passing |
| `model.dropout` | 0.3 | Regularización |
| `training.lr` | 0.001 | Learning rate |
| `training.early_stopping_patience` | 50 | Épocas sin mejora antes de parar |
| `training.model_save_path` | `outputs/models/best_gin_model.pt` | Checkpoint del mejor modelo |
| `evaluation.n_folds` | 5 | Folds para cross-validation |

## Convenciones importantes (Parte 1)

- **Scaffold split obligatorio** — nunca usar split aleatorio para comparar con literatura.
- **NaN manejados con máscara** — no tratar NaN como ceros.
- **`TASK_NAMES`** definido una sola vez en `src/data/dataset.py` (replicado en `viz/config.py` para que el visor no dependa de torch_geometric — ver AUDIT P5).
- **PubChem API**: respetar rate limit (`time.sleep` entre peticiones).
- **GINEConv** (no GINConv): el modelo usa features de enlaces.
- **Corpus demo**: archivos con `"demo": true` son simulados; el visor muestra avisos explícitos.
- **Colores XAI**: generados en `src/xai/visualizer.py` con matplotlib YlOrRd; el 3D usa los mismos hex que el SVG.
- **XAI batch resiliente**: `explain_panama.py` omite SVG/importancias desalineadas (`[SKIP]`) y continúa con el resto del corpus.

## Salidas generadas (Parte 1)

| Ruta | Contenido |
|---|---|
| `data/processed/graphs_*.pt` | Grafos moleculares Tox21 |
| `outputs/models/best_gin_model.pt` | Mejor checkpoint GIN |
| `outputs/results/baseline_results.csv` | AUC por tarea — baselines |
| `outputs/results/gin_results.csv` | AUC por tarea — GNN-GIN |
| `outputs/results/gin_cv_summary.csv` | Resultado 5-fold CV scaffold |
| `outputs/eda/`, `outputs/baselines/` | Gráficos EDA y comparación |
| `data/raw/pubchem_panama_cids.csv` | Corpus panameño (CID, SMILES, familia) |
| `data/raw/pubchem_ghs_labels.csv` | Etiquetas GHS por CID (validación externa) |
| `data/processed/panama_corpus.pt` | Grafos PyG del corpus panameño |
| `outputs/results/panama_predictions.csv` | Predicciones multitarea Fase V |
| `outputs/reports/ghs_validation.csv` | Correlación predicción vs GHS |
| `outputs/reports/report_mida_minsa.pdf` | Reporte institucional |
| `outputs/xai/explanations/*.json` | Explicaciones XAI por compuesto |
| `outputs/xai/figures/*.svg` | Moléculas coloreadas por importancia |

---

# Parte 2 — Proyecto de Análisis de Datos · ChEMBL × Plaguicidas Panamá

Módulo de **ciencia de datos clásica** añadido al repositorio para cumplir los requisitos del curso, manteniendo coherencia temática con el pipeline GNN del proyecto JIC. Reutiliza el corpus PubChem panameño y construye un dataset paralelo de bioactividad ChEMBL para entrenar modelos Random Forest, SVM y SVR.

La documentación detallada vive en [`docs/analisis_proyecto/`](docs/analisis_proyecto/README.md), organizada por **fase del proyecto**. El README de ese módulo incluye el índice completo, la matriz RACI, los archivos clave por fase y los comandos rápidos.

| Referencia transversal | Contenido |
|---|---|
| [`docs/analisis_proyecto/README.md`](docs/analisis_proyecto/README.md) | Índice de fases, RACI, archivos clave, comandos rápidos |
| [`mateo_docs/auditorias/METRICAS_EVALUACION.md`](mateo_docs/auditorias/METRICAS_EVALUACION.md) | Interpretación de splits, accuracy inflada y R² negativo |

## Fases y roles

| Doc | Rol líder | Salida principal |
|---|---|---|
| [Fase 1 — Adquisición](docs/analisis_proyecto/fases/fase1_adquisicion_datos.md) | Ingeniero de Datos | `chembl_panama_bioactivity.csv` |
| [Fase 2 — Limpieza](docs/analisis_proyecto/fases/fase2_limpieza_datos.md) | Ingeniero de Datos | `chembl_clean.csv` |
| [Fase 3 — EDA](docs/analisis_proyecto/fases/fase3_eda.md) | Analista de Datos | Figuras + correlaciones |
| [Fase 4 — Modelado](docs/analisis_proyecto/fases/fase4_modelado.md) | Científico de Datos | Modelos `.pkl` + métricas |
| [Fase 5 — Dashboard](docs/analisis_proyecto/fases/fase5_dashboard.md) | ML Engineer | App FastAPI en `viz/` |
| [Fase 6 — Geodatos](docs/analisis_proyecto/fases/fase6_geodatos.md) | Ingeniero de Datos | `panama_geodata.csv` + GeoJSON |
| [Fase 7 — Comunicación](docs/analisis_proyecto/fases/fase7_comunicacion.md) | Todos | Artículo IEEE + video + slides |

## Código fuente del módulo

| Módulo | Rol |
|---|---|
| `src/analisis_proyecto/chembl_api.py` | Descarga y construcción del dataset (Flujo A — REST) |
| `src/analisis_proyecto/chembl_local.py` | Extracción SQLite offline (Flujo A — dump local) |
| `src/analisis_proyecto/chembl_extract.py` | Fachada unificada de extracción ChEMBL |
| `src/analisis_proyecto/chembl_preprocessing.py` | EDA, missingno, imputación, splits (Flujo B) |
| `src/analisis_proyecto/geodata_panama.py` | Geodatos Panamá: distritos + INEC (Flujo D) |
| `scripts/analisis_proyecto/fase1/extract_chembl_local.py` | CLI extracción ChEMBL (Fase 1) |
| `scripts/analisis_proyecto/fase1/verify_chembl_db.py` | Diagnóstico ChEMBLdb (Fase 1) |
| `scripts/analisis_proyecto/fase4/verify_flow_b.py` | Verificación end-to-end Flujo B (Fase 4) |
| `scripts/analisis_proyecto/fase5/03_prepare_dashboard_data.py` | Shim → `scripts/fase5/prepare_dashboard.py` (Fase 5) |
| `scripts/analisis_proyecto/fase5/test_dashboard.py` | Shim → smoke test del dashboard (Fase 5) |
| `scripts/analisis_proyecto/fase6/02_download_geodata.py` | CLI geodatos Panamá (Fase 6) |
| `scripts/fase5/prepare_dashboard.py` | Genera artefactos JSON para dashboard |

## Ejecución rápida

```bash
cd JIC2026
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Etapa 00 — extracción ChEMBL (requiere dump SQLite o backend API)
make chembl-extract
jupyter notebook "notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb"
make test-chembl-flow-b
# Notebooks por fase:
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Etapa 02 — dashboard web
make prepare-dashboard
make viz
# → http://127.0.0.1:8000/eda          (EDA ChEMBL)
# → http://127.0.0.1:8000/chembl/models (modelos sklearn + predictor RF)
# → http://127.0.0.1:8000/panama/map    (mapa distritos)
```

## Plan maestro

[mateo_docs/planes/EXPANSION_CHEMBL_PLAN.md](mateo_docs/planes/EXPANSION_CHEMBL_PLAN.md)

---

# Visor web — GNN-Tox Viewer (común a ambas partes)

Dashboard FastAPI unificado para explorar toxicidad molecular con explicabilidad integrada y analítica ChEMBL/Panamá. El visor **no requiere recompilar el frontend** — plantillas Jinja2 + JavaScript estático.

## Arranque

**Sin modelo entrenado** (corpus demo con predicciones simuladas):

```bash
make setup-viz    # instala deps FastAPI + genera corpus demo
make viz          # http://127.0.0.1:8000
```

**Con modelo entrenado** (predicciones y XAI reales):

```bash
make train-gin
make setup-viz-full    # corpus con inferencia real
make viz
```

Comandos adicionales:

```bash
make viz VIZ_PORT=8765   # puerto personalizado
make viz-lan             # accesible en la red local (0.0.0.0)
make viz-prod            # sin auto-reload (presentaciones)
make build-viz-corpus-demo   # solo regenerar JSON demo
make build-viz-corpus        # solo regenerar con modelo real
```

## Páginas

| Ruta | Parte | Descripción |
|---|---|---|
| `/` | JIC | Visor 3D del corpus precomputado (filtros por riesgo/familia) |
| `/molecule/{id}` | JIC | Vista detallada 3D + 2D + XAI de un compuesto |
| `/analyze?smiles=...` | JIC | Análisis ad-hoc de un SMILES arbitrario |
| `/eda` | Analítica | Exploración ChEMBL: histogramas, boxplots, correlación |
| `/chembl/models` | Analítica | Matrices de confusión + ROC + R² + predictor pChEMBL interactivo |
| `/panama/toxicity` | Analítica | Heatmap Tox21 (235 plaguicidas × 12 vías) + XAI por compuesto |
| `/panama/map` | Analítica | Choropleth distritos con disclaimer INEC (AUDIT P6) |
| `/panama/models` | Analítica | Comparativa baselines vs GIN (AUDIT P9) |
| `/health` | Común | Health check para despliegue cloud (AUDIT P12) |

## Funcionalidades del visor 3D

| Función | Descripción |
|---|---|
| **Corpus Panamá** | Plaguicidas pre-cargados (clorpirifos, atrazina, tebuconazol, etc.) |
| **Análisis en vivo** | Predicción + XAI sobre cualquier SMILES válido (requiere modelo) |
| **Visor 3D** | Estructura molecular interactiva con [3Dmol.js](https://3dmol.csb.pitt.edu/) |
| **Visor 2D** | SVG RDKit coloreado por importancia XAI (paleta YlOrRd) |
| **Coloración unificada** | Mismos colores hex en 3D y 2D, calculados en servidor |
| **Grad-CAM / GNNExplainer** | Selector de método y diana biológica Tox21 |
| **Tabla de átomos** | Importancia por átomo con hover sincronizado al 3D |
| **Propiedades** | Peso molecular, LogP, TPSA, fórmula (RDKit) |

## API REST

### Visor GNN (`/api/...`)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/status` | GET | Estado del modelo y corpus |
| `/api/corpus` | GET | Lista de compuestos pre-computados |
| `/api/corpus/{id}` | GET | Datos completos de un compuesto |
| `/api/predict` | POST | Predicción multitarea sobre SMILES |
| `/api/explain` | POST | Explicación XAI (gradcam o gnnexplainer) |
| `/api/analyze` | POST | Predicción + XAI completo |
| `/api/mol3d` | GET | Estructura 3D (SDF) desde SMILES |
| `/api/properties` | GET | Propiedades fisicoquímicas |
| `/api/svg` | POST | SVG 2D coloreado + `atom_colors` |
| `/api/xai-colors` | POST | Colores hex YlOrRd para un vector de importancias |
| `/api/tasks` | GET | Lista de tareas Tox21 con descripciones |

### Analítica ChEMBL/Panamá (`/api/analytics/...`)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/analytics/chembl/meta` | GET | Metadatos para selectores EDA |
| `/api/analytics/chembl/data` | GET | Datos para histograma, boxplot, scatter |
| `/api/analytics/chembl/correlation` | GET | Matriz Pearson (heatmap) |
| `/api/analytics/models/eval` | GET | Confusión, ROC y R² de los 4 modelos sklearn |
| `/api/analytics/models/features` | GET | Features del predictor + etiquetas |
| `/api/analytics/models/predict` | POST | Predicción pChEMBL para inputs del usuario |
| `/api/analytics/models/comparison` | GET | Baselines vs GIN (AUDIT P9) |
| `/api/analytics/metrics/summary` | GET | CSV crudo de métricas por modelo/split |
| `/api/analytics/toxicity/profile` | GET | Heatmap Tox21 filtrado por familia/alerta |
| `/api/analytics/toxicity/xai` | GET | URL del SVG GNNExplainer/Grad-CAM |
| `/api/analytics/geo` | GET | GeoJSON distritos con disclaimer INEC |
| `/api/analytics/geo/summary` | GET | Agregado por provincia para choropleth |
| `/api/analytics/refresh` | POST | Invalida la caché por checksum (AUDIT P3) |

## Generar corpus precomputado

```bash
python scripts/fase4/build_viz_corpus.py --demo    # sin modelo (UI de prueba)
python scripts/fase4/build_viz_corpus.py           # con outputs/models/best_gin_model.pt
```

Cada compuesto se guarda en `viz/data/{id}.json` con predicciones, importancias XAI, colores por átomo, propiedades y estructura 3D.

> **Nota:** Los compuestos marcados como **«Ejemplo de prueba»** en el dashboard usan datos simulados (`demo: true`). No son predicciones del modelo entrenado.

---

## Comandos Makefile (referencia rápida)

### Setup y entrenamiento (Parte 1)

| Comando | Descripción |
|---|---|
| `make setup` | Crea venv e instala `requirements.txt` |
| `make install-pyg-ext` | Extensiones PyG aceleradas (torch-scatter, etc.) |
| `make check-gin-gpu` | Verifica disponibilidad CUDA |
| `make prepare-graphs` | Genera grafos Tox21 |
| `make train-baselines` | Entrena modelos de referencia |
| `make train-gin` | Entrena GNN-GIN |
| `make train-gin-cv` | 5-fold CV scaffold (AUDIT E2) |
| `make train-gin-all` | Grafos + entrenamiento GIN |
| `make eda` | Ejecuta notebook EDA |

### Aplicación Panamá (Parte 1, Fase V)

| Comando | Descripción |
|---|---|
| `make build-panama-corpus` | Corpus Panamá desde PubChem + GHS |
| `make build-panama-corpus-fast` | Corpus sin descarga GHS |
| `make explain-panama` | Predicciones + XAI sobre corpus panameño |
| `make validate-ghs` | Correlación predicciones vs GHS |
| `make generate-panama-report` | Reporte MIDA/MINSA |
| `make panama-all` | Pipeline Fase V completo |

### Analítica ChEMBL (Parte 2)

| Comando | Descripción |
|---|---|
| `make chembl-extract` | Extracción ChEMBL (SQLite o API según config) |
| `make test-chembl-flow-b` | Verificación end-to-end Flujo B + entrenamiento RF/SVM/SVR |
| `make prepare-dashboard` | Genera artefactos JSON para el dashboard |
| `make download-geodata` | Descarga distritos Panamá + tabla INEC |

### Visor web (común)

| Comando | Descripción |
|---|---|
| `make setup-viz` | Visor: deps + corpus demo |
| `make setup-viz-full` | Visor: deps + corpus con modelo real |
| `make viz` | Arranca servidor en http://127.0.0.1:8000 |
| `make viz-lan` | Servidor accesible en red local |
| `make viz-prod` | Sin auto-reload (presentaciones) |
| `make viz-check` | Smoke test de la aplicación FastAPI |
| `make build-viz-corpus` | Regenera corpus con modelo real |
| `make build-viz-corpus-demo` | Regenera corpus con datos demo |

---

## Licencia y contexto

Proyecto de investigación para **JIC 2026** (Jornada de Iniciación Científica) y para el **proyecto de Análisis de Datos** del curso, ambos sobre el dominio de toxicidad de plaguicidas registrados por el MIDA de Panamá. Las predicciones son herramientas de priorización e investigación, **no sustituyen** evaluación toxicológica oficial. Los datos sociodemográficos mostrados en el mapa de Panamá son estimaciones reproducibles construidas a partir del área y promedios provinciales referenciados al INEC; no son datos oficiales descargados de MAPI (ver disclaimer en `/panama/map` y AUDIT P6).
