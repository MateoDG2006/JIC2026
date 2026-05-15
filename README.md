# GNN-GIN + XAI — toxicidad de agroquímicos (Panamá / Tox21)

Base del código alineada con `docs/*.md`, `AGENTS.md` y `CLAUDE.md`.

## Estructura

- `src/data/` — featurizer, dataset, splitter, PubChem
- `src/models/` — GIN, baselines
- `src/training/` — pérdida enmascarada, entrenamiento, métricas
- `src/evaluation/` — AUC multitarea, coherencia química, folds de CV
- `src/xai/` — GNNExplainer, Grad-CAM, visualizador RDKit
- `config/config.yaml` — hiperparámetros
- `scripts/prepare_tox21_graphs.py` — genera `data/processed/graphs_*.pt` vía DeepChem
- `phase2_baselines/train_baselines.py` — Fase II: RF, MLP, SMILES2vec → `outputs/results/baseline_results.csv`

## Entorno virtual

Se recomienda **Python 3.10** (compatible con RDKit, DeepChem y el resto del stack; versiones muy nuevas pueden dejar fuera paquetes antiguos).

**Windows (PowerShell)** — crear el entorno con una versión concreta usando el *launcher* `py`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD)**:

```bat
py -3.10 -m venv .venv
.venv\Scripts\activate.bat
```

Si no tienes `py`, usa la ruta completa al `python.exe` de esa versión:

```powershell
& "C:\Ruta\a\Python310\python.exe" -m venv .venv
```

**macOS / Linux**:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

Con el entorno activado, el prompt suele mostrar `(.venv)`; las dependencias se instalan solo ahí.

## Instalación

Con el entorno virtual **activado**, instalar dependencias (RDKit, PyTorch, PyG, DeepChem, etc.):

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Primeros pasos

Desde la raíz del repo, con el entorno virtual activado:

```bash
python scripts/prepare_tox21_graphs.py
python phase2_baselines/train_baselines.py
```

La fase II (baselines) vive en la carpeta `phase2_baselines/`; detalle en `phase2_baselines/README.md` y `docs/task_train_baselines.md`.
