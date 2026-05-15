# Predicción de toxicidad de agroquímicos con GNN-GIN y XAI

Sistema de **química computacional** que modela moléculas como **grafos** (átomos = nodos, enlaces = aristas), entrena una **GNN tipo GIN** sobre el benchmark **Tox21** (12 tareas de toxicidad) y prevé incorporar **explicabilidad** (GNNExplainer, Grad-CAM) y aplicación a un **corpus de plaguicidas** enlazado a fuentes públicas (PubChem, contexto MIDA/MINSA Panamá).

---

## Página de presentación (resumen ejecutivo)

| | |
| --- | --- |
| **Problema** | Evaluar el perfil de toxicidad multitarea de plaguicidas de interés regulatorio sin depender solo de ensayos costosos; comparar enfoques clásicos (fingerprints + ML) frente a GNN sobre grafo molecular. |
| **Idea central** | Representación molecular nativa (grafo) + **GIN** (mensajes agregados, ε entrenable) + *readout* **mean + max** → vector global → cabeza multitarea (12 salidas). **Scaffold split** (Murcko) para medir generalización a esqueletos nuevos, no memorización. |
| **Datos** | **Tox21** vía DeepChem (`molnet.load_tox21`), 12 dianas; etiquetas con **NaN** por tarea → pérdida **BCE con máscara** (`MaskedBCELoss`). Corpus Panamá: línea de trabajo documentada en `docs/06_aplicacion_panama.md` y `src/data/pubchem_api.py`. |
| **Baselines (Fase II)** | Random Forest + Morgan, MLP + Morgan, SMILES2vec — mismo protocolo de evaluación; umbrales y salidas en `phase2_baselines/README.md`. |
| **Objetivos de rendimiento (referencia)** | GNN: AUC-ROC medio **> 0.82** en test con scaffold; baselines alineados con literatura MoleculeNet (RF ~0.77 suele citarse en **split aleatorio**; con scaffold las medias son más bajas — ver avisos en `phase2_baselines/README.md`). |
| **XAI e impacto** | Resaltar **átomos/subestructuras** asociados a la predicción por tarea; validación química y cruce con datos externos (GHS PubChem, PPDB) según `docs/05_xai.md` y `docs/06_aplicacion_panama.md`. |
| **Entregables de código** | Grafos procesados (`data/processed/graphs_*.pt`), resultados de baselines (`outputs/results/baseline_results.csv`), checkpoints GNN (`outputs/models/` según `config.yaml`), figuras y reportes bajo `outputs/`. |

**Hipótesis (documentada en `docs/00_indice.md`):** una GNN-GIN entrenada en grafos Tox21 predice el perfil multitarea de plaguicidas panameños con **AUC-ROC superior** a QSAR clásico bajo el mismo protocolo, y las explicaciones XAI son **coherentes** con grupos funcionales y mecanismos descritos en literatura.

---

## Explicación del proyecto

### Por qué grafos y GIN

- **Grafo molecular:** invariante a reordenamiento de átomos, sin inventar 5000 descriptores a mano; la señal es local (vecinos químicos) y global (*pooling*).
- **GIN (Graph Isomorphism Network):** agrega vecinos con suma (multiplicidad importa) y MLP; en la práctica suele funcionar bien en benchmarks moleculares frente a GCN “promedio”.
- **Mean + max pooling:** el promedio captura composición global; el máximo evita perder **átomos muy activos** (outliers) en la representación del grafo.

### Flujo general

1. **Datos:** SMILES → canonicalización (RDKit) → featurizado a `torch_geometric.data.Data` (`src/data/featurizer.py`).
2. **Split:** por **scaffold** (`src/data/splitter.py`) — misma familia esquelética no cruza train/val/test.
3. **Entrenamiento:** logits + `BCEWithLogitsLoss` enmascarado donde no hay medición (`src/training/loss.py`); métricas **AUC-ROC por tarea** (`src/evaluation/`, `src/training/metrics.py`).
4. **Baselines:** entrenamiento desde `phase2_baselines/train_baselines.py` (ver `docs/03_baselines.md`).
5. **GNN:** arquitectura en `src/models/gin.py`, bucle y evaluación en `src/training/trainer.py` y `docs/04_entrenamiento.md`.
6. **XAI:** `src/xai/` — ver `docs/05_xai.md`.

### Convenciones importantes (resumen de `AGENTS.md`)

- No usar **split aleatorio** para comparar con publicaciones que usan scaffold.
- No entrenar ignorando **NaN** como si fueran ceros.
- Nombres de tareas Tox21: constante **`TASK_NAMES`** en `src/data/dataset.py` (no duplicar en otros módulos).
- PubChem: respetar **rate limit** (`time.sleep` entre peticiones) en `src/data/pubchem_api.py`.

---

## Configuración del proyecto

La fuente única de hiperparámetros de experimentos es **`config/config.yaml`**. Los scripts y el entrenador deben leerla (o una copia con sufijo, p. ej. `config_d256_L5.yaml`) para mantener reproducibilidad.

### Sección `model`

| Clave | Valor por defecto | Rol |
| --- | --- | --- |
| `node_feat_dim` | `45` | Dimensión del vector de nodo del featurizador; debe coincidir con `src/data/featurizer.py`. |
| `hidden_dim` | `128` | Dimensión oculta GIN y proyección inicial; probar `256` en ablaciones. |
| `n_layers` | `3` | Capas de paso de mensajes GIN; probar `4`–`5` si hay infraestructura. |
| `n_tasks` | `12` | Salidas multitarea (= número de tareas Tox21 en `TASK_NAMES`). |
| `dropout` | `0.3` | Regularización en GIN y clasificador. |

### Sección `training`

| Clave | Valor por defecto | Rol |
| --- | --- | --- |
| `lr` | `0.001` | Tasa de aprendizaje (p. ej. Adam). |
| `batch_size` | `32` | Tamaño de lote para `DataLoader` PyG. |
| `max_epochs` | `250` | Tope de épocas por corrida. |
| `early_stopping_patience` | `50` | Épocas sin mejora en métrica de validación antes de parar. |
| `grad_clip_norm` | `1.0` | Recorte de gradiente global (estabilidad GNN). |
| `model_save_path` | `outputs/models/best_gin_model.pt` | Checkpoint del **mejor** modelo según validación (no guardar cada época). |

### Sección `scheduler`

| Clave | Valor por defecto | Rol |
| --- | --- | --- |
| `factor` | `0.5` | Factor de reducción de LR en `ReduceLROnPlateau`. |
| `patience` | `20` | Paciencia del scheduler (épocas sin mejora en la métrica monitorizada). |

Monitorizar **`val_auc` en modo `max`**: el scheduler recibe el AUC de validación positivo.

### Sección `evaluation`

| Clave | Valor por defecto | Rol |
| --- | --- | --- |
| `n_folds` | `5` | Número de folds en validación cruzada (protocolo en `src/evaluation/cross_validation.py` y `docs/04_entrenamiento.md`). |
| `split` | `scaffold` | Tipo de partición obligatorio para comparaciones válidas con el estado del arte en Tox21. |

### Sección `wandb`

| Clave | Valor por defecto | Rol |
| --- | --- | --- |
| `project` | `gnn-toxicity-panama` | Nombre del proyecto en Weights & Biases. |
| `entity` | `null` | Sustituir por tu equipo/usuario W&B si aplica. |

---

## Requisitos y entorno

Se recomienda **Python 3.10** (RDKit, DeepChem, PyTorch/PyG; versiones muy nuevas pueden romper dependencias).

**Windows (PowerShell):**

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Stack principal** (`requirements.txt`): NumPy, Pandas, scikit-learn, PyYAML, Requests, PyTorch ≥ 2.0, PyTorch Geometric ≥ 2.4, RDKit ≥ 2023.9, DeepChem ≥ 2.7, wandb, matplotlib, seaborn, captum, pytest.

---

## Estructura del repositorio

| Ruta | Contenido |
| --- | --- |
| `config/config.yaml` | Hiperparámetros del modelo y del entrenamiento |
| `src/data/` | Featurizador, dataset PyG, splitter, API PubChem |
| `src/models/` | GIN (`gin.py`), baselines (`baselines.py`) |
| `src/training/` | Pérdida enmascarada, *trainer*, métricas |
| `src/evaluation/` | AUC multitarea, CV, coherencia química |
| `src/xai/` | GNNExplainer, Grad-CAM, visualización RDKit |
| `scripts/prepare_tox21_graphs.py` | Genera `data/processed/graphs_{train,val,test}.pt` |
| `phase2_baselines/` | Entrada Fase II: RF, MLP, SMILES2vec → CSV de resultados |
| `docs/` | Documentación por fases (`00_indice.md` … `06_aplicacion_panama.md`) |
| `reports/` | Auditorías y listas de issues/resolución |
| `CLAUDE.md` / `AGENTS.md` | Planificación larga y reglas de desarrollo para el equipo y agentes |

---

## Primeros pasos (desde la raíz del repo)

Con el entorno virtual **activado**:

```bash
# 1) Construir tensores de grafos Tox21 para train/val/test
python scripts/prepare_tox21_graphs.py

# 2) Fase II — baselines (escribe outputs/results/baseline_results.csv)
python phase2_baselines/train_baselines.py
```

Opciones útiles de baselines: `python phase2_baselines/train_baselines.py --label-stats` o `-v` (ver `phase2_baselines/README.md`).

El entrenamiento GNN y el CV están descritos en **`docs/04_entrenamiento.md`** y enlazados con `src/training/trainer.py` y `src/evaluation/cross_validation.py`.

---

## Documentación relacionada

| Documento | Uso |
| --- | --- |
| [docs/00_indice.md](docs/00_indice.md) | Índice, hipótesis, cronograma 10 semanas, tabla de métricas |
| [docs/01_pipeline_datos.md](docs/01_pipeline_datos.md) | Grafo SMILES, splits, NaN |
| [docs/02_modelo_gin.md](docs/02_modelo_gin.md) | Arquitectura GIN |
| [docs/03_baselines.md](docs/03_baselines.md) | Baselines |
| [docs/04_entrenamiento.md](docs/04_entrenamiento.md) | Loop, scheduler, CV |
| [docs/05_xai.md](docs/05_xai.md) | Explicabilidad |
| [docs/06_aplicacion_panama.md](docs/06_aplicacion_panama.md) | Corpus Panamá y reportes |
| [docs/task_train_baselines.md](docs/task_train_baselines.md) | Tarea detallada Fase II |
| [AGENTS.md](AGENTS.md) | Reglas de código y ML del repositorio |
| [CLAUDE.md](CLAUDE.md) | Planificación extendida y referencias |

---

## Tests

```bash
pytest
```

---

## Licencia y contexto institucional

Proyecto orientado a apoyo de lectura científica y regulatoria (MIDA, MINSA, agricultura de exportación en Panamá). Las predicciones **no sustituyen** evaluación toxicológica oficial; son herramientas de priorización e investigación.
