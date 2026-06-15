# Predicción de Toxicidad de Agroquímicos con GNN-GIN y XAI

Sistema de **química computacional** que modela moléculas como **grafos** (átomos = nodos, enlaces = aristas), entrena una **GNN tipo GIN** sobre el benchmark **Tox21** (12 tareas de toxicidad) e incorpora **explicabilidad** (GNNExplainer, Grad-CAM) para identificar qué grupos funcionales causan la toxicidad predicha. Orientado a la evaluación de **plaguicidas registrados en Panamá** (MIDA/MINSA).

---

## Idea central

| Aspecto | Detalle |
|---|---|
| **Problema** | Evaluar el perfil de toxicidad multitarea de plaguicidas sin depender solo de ensayos costosos |
| **Enfoque** | Grafo molecular + GIN (mensajes agregados con suma) + readout mean+max + cabeza multitarea (12 salidas) |
| **Datos** | Tox21 via DeepChem (~8000 moléculas, 12 ensayos biológicos, datos faltantes manejados con MaskedBCELoss) |
| **Split** | Scaffold de Murcko (sin filtración entre train/test) |
| **Baselines** | Random Forest, MLP, SMILES2vec — misma evaluación para comparación justa |
| **XAI** | GNNExplainer + Grad-CAM para identificar átomos responsables de la toxicidad |
| **Objetivo** | AUC-ROC medio > 0.82 en test con scaffold split |

**Hipótesis:** Una GNN-GIN entrenada en grafos Tox21 predice el perfil de toxicidad de plaguicidas panameños con AUC-ROC superior a modelos QSAR clásicos, y las explicaciones XAI identifican grupos funcionales coherentes con mecanismos documentados.

---

## Estructura del repositorio

```
JIC2026/
├── config/
│   └── config.yaml              # Hiperparámetros del modelo y entrenamiento
│
├── src/
│   ├── data/
│   │   ├── featurizer.py        # SMILES → grafo PyG (45 node features, 9 edge features)
│   │   ├── dataset.py           # ToxicityDataset + TASK_NAMES (12 tareas)
│   │   ├── splitter.py          # Scaffold split de Murcko
│   │   └── pubchem_api.py       # Cliente PubChem API (corpus panameño, NO entrenamiento)
│   ├── models/
│   │   ├── gin.py               # Arquitectura GNN-GIN (GINEConv + residual)
│   │   └── baselines.py         # RF, MLP, SMILES2vec (modelos de referencia)
│   ├── training/
│   │   ├── trainer.py           # Loop de entrenamiento con early stopping
│   │   ├── loss.py              # MaskedBCELoss (ignora NaN + pos_weight)
│   │   └── metrics.py           # Re-exporta métricas de evaluación
│   ├── xai/
│   │   ├── gnn_explainer.py     # GNNExplainer con _SingleTaskWrapper
│   │   ├── grad_cam.py          # Grad-CAM adaptado a grafos
│   │   └── visualizer.py        # Moléculas SVG coloreadas por importancia
│   └── evaluation/
│       ├── cross_validation.py  # AUC-ROC/AUPRC multitarea + scaffold folds
│       └── chemical_coherence.py # Validación de XAI con patrones SMARTS
│
├── scripts/
│   ├── prepare_tox21_graphs.py  # Descarga Tox21 → genera graphs_*.pt
│   └── train_baselines.py       # Entrena RF + MLP + SMILES2vec
│
├── notebooks/
│   ├── 01_eda_tox21.ipynb       # EDA completo del dataset Tox21 (16 gráficos)
│   └── 02_baselines_tox21.ipynb # Entrenamiento y evaluación de 3 baselines (10 gráficos)
│
├── docs/
│   ├── fase1_pipeline_datos.md  # Documentación del pipeline de datos
│   ├── fase2_baselines.md       # Documentación de baselines
│   ├── fase3_modelo_gin.md      # Documentación del modelo GNN-GIN
│   ├── fase4_xai.md             # Documentación de explainability
│   └── fase5_panama.md          # Documentación de aplicación a Panamá
│
├── tests/                       # Tests unitarios (pytest)
├── data/                        # Datos crudos y procesados (no en git)
├── outputs/                     # Modelos, resultados, gráficos (no en git)
├── CLAUDE.md                    # Planificación detallada del proyecto
└── README.md                    # Este archivo
```

---

## Primeros pasos

### 1. Instalar dependencias

```bash
# Crear entorno (Python 3.10–3.12; deepchem no soporta 3.13+)
conda create -n toxgnn python=3.10
conda activate toxgnn
conda install -c conda-forge rdkit

# PyTorch con soporte GPU (CUDA 12.4)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# PyTorch Geometric (ajusta la URL de torch si usas otra versión CUDA)
pip install torch_geometric torch_scatter torch_sparse torch_cluster \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html

pip install -r requirements.txt
```

Alternativa con Makefile (venv local en `.venv/`):

```bash
make setup
# PyTorch con GPU + extensiones PyG (torch-scatter acelera max_pool)
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
make install-pyg-ext
```

Si ves el warning `torch-scatter package, but it was not found`, instala las extensiones:

```bash
make install-pyg-ext
```

Verificar que la GPU está disponible:

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Si `CUDA: False`, PyTorch se instaló sin soporte GPU. Reinstala con el comando `cu124` de arriba (ajusta `cu124` a la versión de CUDA de tu driver NVIDIA; ver [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)).

### 2. Preparar datos de entrenamiento

```bash
python scripts/prepare_tox21_graphs.py
```
Esto descarga Tox21 desde DeepChem, convierte ~8000 moléculas a grafos PyG, y guarda `data/processed/graphs_{train,val,test}.pt`.

### 3. Entrenar baselines (Fase II)

```bash
python scripts/train_baselines.py
python scripts/train_baselines.py -v            # modo verbose
python scripts/train_baselines.py --label-stats # ver distribución de clases
```

### 4. Análisis exploratorio

Abrir el notebook `notebooks/01_eda_tox21.ipynb` en Jupyter. Genera 16 gráficos en `outputs/eda/`:
distribución de clases, patrones de NaN, co-ocurrencia de toxicidad, propiedades moleculares,
scaffolds, calidad del split, Lipinski, etc.

### 5. Tests

```bash
pytest
```

---

## Las 5 fases del proyecto

| Fase | Descripción | Documentación |
|---|---|---|
| I | Pipeline de datos: SMILES → grafos, scaffold split, corpus panameño | [docs/fase1_pipeline_datos.md](docs/fase1_pipeline_datos.md) |
| II | Baselines: RF, MLP, SMILES2vec como referencia | [docs/fase2_baselines.md](docs/fase2_baselines.md) |
| III | Modelo GNN-GIN: arquitectura, entrenamiento, 5-fold CV | [docs/fase3_modelo_gin.md](docs/fase3_modelo_gin.md) |
| IV | XAI: GNNExplainer, Grad-CAM, validación química | [docs/fase4_xai.md](docs/fase4_xai.md) |
| V | Aplicación a plaguicidas de Panamá, reportes MIDA/MINSA | [docs/fase5_panama.md](docs/fase5_panama.md) |

---

## Configuración (config/config.yaml)

| Parámetro | Default | Descripción |
|---|---|---|
| `model.hidden_dim` | 128 | Dimensión oculta de las capas GIN |
| `model.n_layers` | 3 | Capas de message passing |
| `model.dropout` | 0.3 | Regularización |
| `training.lr` | 0.001 | Learning rate |
| `training.early_stopping_patience` | 50 | Épocas sin mejora antes de parar |
| `evaluation.n_folds` | 5 | Folds para cross-validation |

---

## Convenciones importantes

- **Scaffold split obligatorio** — nunca usar split aleatorio para comparar con literatura
- **NaN manejados con máscara** — no tratar NaN como ceros
- **TASK_NAMES** definido una sola vez en `src/data/dataset.py`
- **PubChem API**: respetar rate limit (time.sleep entre peticiones)
- **GINEConv** (no GINConv): el modelo usa features de enlaces

---

## Licencia y contexto

Proyecto de investigación para JIC 2026 (Jornada de Iniciación Científica). Las predicciones son herramientas de priorización e investigación, **no sustituyen** evaluación toxicológica oficial.
