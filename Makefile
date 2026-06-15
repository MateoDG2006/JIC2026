PYTHON_WSL := python3
VENV_DIR := .venv
CONFIG := config/config.yaml

# Proyecto requiere Python 3.10–3.12 (deepchem no soporta 3.13+).
ifeq ($(OS),Windows_NT)
  PYTHON_PS := py -3.10
  VENV_PYTHON := $(CURDIR)/$(VENV_DIR)/Scripts/python.exe
  RM_RF := rmdir /s /q
else
  PYTHON_PS := python3.10
  VENV_PYTHON := $(CURDIR)/$(VENV_DIR)/bin/python
  RM_RF := rm -rf
endif

# ── Entorno ───────────────────────────────────────────────────────────────

setup:
	$(PYTHON_PS) -m venv $(VENV_DIR)
	"$(VENV_PYTHON)" -m pip install --upgrade pip
	"$(VENV_PYTHON)" -m pip install -r requirements.txt

# Extensiones PyG aceleradas (torch-scatter, etc.) — requiere PyTorch cu124 ya instalado
install-pyg-ext:
	"$(VENV_PYTHON)" -m pip install torch_scatter torch_sparse torch_cluster \
		-f https://data.pyg.org/whl/torch-2.6.0+cu124.html

clean:
ifeq ($(OS),Windows_NT)
	if exist $(VENV_DIR) $(RM_RF) $(VENV_DIR)
else
	$(RM_RF) $(VENV_DIR)
endif

# ── Datos (Fase I) ────────────────────────────────────────────────────────

prepare-graphs:
	"$(VENV_PYTHON)" scripts/prepare_tox21_graphs.py

powershell-extract-data-from-tox21: prepare-graphs

wsl-extract-data-from-tox21: prepare-graphs

eda:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/01_eda_tox21.ipynb

# ── Baselines (Fase II) ───────────────────────────────────────────────────

baselines:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/02_baselines_tox21.ipynb

train-baselines:
	"$(VENV_PYTHON)" scripts/train_baselines.py

train-baselines-verbose:
	"$(VENV_PYTHON)" scripts/train_baselines.py -v

# ── GNN-GIN (Fase III) ────────────────────────────────────────────────────
# Requisito: make prepare-graphs (genera data/processed/graphs_*.pt)

train-gin:
	"$(VENV_PYTHON)" scripts/train_gin.py --config $(CONFIG)

train-gin-verbose:
	"$(VENV_PYTHON)" scripts/train_gin.py --config $(CONFIG) -v

train-gin-wandb:
	"$(VENV_PYTHON)" scripts/train_gin.py --config $(CONFIG) -v --wandb

# Pipeline completo: grafos + entrenamiento GIN
train-gin-all: prepare-graphs train-gin

train-gin-all-verbose: prepare-graphs train-gin-verbose

check-gin-gpu:
	"$(VENV_PYTHON)" -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

# ── Visualización XAI (FastAPI) ───────────────────────────────────────────
# Requisitos: make setup (entorno principal) antes de setup-viz.
# Sin modelo entrenado: make setup-viz  → corpus demo + servidor.
# Con modelo: make setup-viz-full tras make train-gin.
#
# Uso (no hace falta activar el venv: make usa .venv/Scripts/python.exe):
#   make setup-viz    → instalar deps + corpus demo
#   make viz          → http://127.0.0.1:8000
#   make viz VIZ_PORT=8765
#   make viz-lan      → accesible en la red local

VIZ_HOST := 127.0.0.1
VIZ_PORT := 8000

install-viz:
	"$(VENV_PYTHON)" -m pip install -r viz/requirements.txt

build-viz-corpus:
	"$(VENV_PYTHON)" scripts/build_viz_corpus.py

build-viz-corpus-demo:
	"$(VENV_PYTHON)" scripts/build_viz_corpus.py --demo

# Instala deps del visor y genera corpus demo (no requiere modelo)
setup-viz: install-viz build-viz-corpus-demo

# Instala deps y genera corpus con predicciones reales (requiere best_gin_model.pt)
setup-viz-full: install-viz build-viz-corpus

viz-check:
	"$(VENV_PYTHON)" scripts/viz_serve.py --check-only

viz: viz-check
	"$(VENV_PYTHON)" scripts/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT) --reload

viz-serve: viz

# Acceso desde otros dispositivos en la misma red (puerto 8000 por defecto)
viz-lan: viz-check
	"$(VENV_PYTHON)" scripts/viz_serve.py --host 0.0.0.0 --port $(VIZ_PORT) --reload

# Servidor sin auto-reload (mas estable en demos/presentaciones)
viz-prod: viz-check
	"$(VENV_PYTHON)" scripts/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT)

.PHONY: setup install-pyg-ext clean prepare-graphs powershell-extract-data-from-tox21 wsl-extract-data-from-tox21 eda baselines train-baselines train-baselines-verbose train-gin train-gin-verbose train-gin-wandb train-gin-all train-gin-all-verbose check-gin-gpu install-viz build-viz-corpus build-viz-corpus-demo setup-viz setup-viz-full viz-check viz viz-serve viz-lan viz-prod
