# JIC2026 — Makefile unificado (GNN-JIC + proyecto analisis)
# Ejecutar siempre desde la raíz del repositorio.
# Ayuda: make  |  make help

.DEFAULT_GOAL := help

PYTHON_WSL := python3
VENV_DIR := .venv
CONFIG := config/config.yaml
ANALISIS_DIR := proyecto analisis
ANALISIS_CONFIG := $(ANALISIS_DIR)/config/config.yaml

ifeq ($(OS),Windows_NT)
  PYTHON_PS := py -3.10
  VENV_PYTHON := $(CURDIR)/$(VENV_DIR)/Scripts/python.exe
  RM_RF := rmdir /s /q
else
  PYTHON_PS := python3.10
  VENV_PYTHON := $(CURDIR)/$(VENV_DIR)/bin/python
  RM_RF := rm -rf
endif

# ── Rutas compartidas ───────────────────────────────────────────────────────

MODEL := outputs/models/best_gin_model.pt
PANAMA_CORPUS := data/processed/panama_corpus.pt
PANAMA_PREDICTIONS := outputs/results/panama_predictions.csv
GHS_LABELS := data/raw/pubchem_ghs_labels.csv

CHEMBL_COMPOSE := docker compose -f "$(ANALISIS_DIR)/docker/docker-compose.yml"
CHEMBL_VOLUME := jic2026_chembl_db
CHEMBL_NOTEBOOK := $(ANALISIS_DIR)/notebooks/fase1_adquisicion.ipynb

VIZ_HOST := 127.0.0.1
VIZ_PORT := 8000
ANALISIS_VIZ_PORT := 8001

# ═══════════════════════════════════════════════════════════════════════════
# AYUDA (target por defecto)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help
help:
	@echo.
	@echo   JIC2026 — Makefile unificado
	@echo   Raiz: $(CURDIR)
	@echo.
	@echo   === Entorno (comun) ===
	@echo   make setup                  Crear .venv e instalar requirements.txt (JIC)
	@echo   make setup-analisis         Instalar requirements de proyecto analisis/
	@echo   make install-pyg-ext        Extensiones PyG (torch-scatter, etc.; requiere PyTorch cu124)
	@echo   make clean                  Eliminar .venv
	@echo   make check-gin-gpu          Comprobar CUDA / GPU
	@echo.
	@echo   === JIC — Datos y baselines (Fases I-II) ===
	@echo   make prepare-graphs         Tox21 DeepChem -^> data/processed/graphs_*.pt
	@echo   make eda                    Ejecutar notebook 01_eda_tox21.ipynb
	@echo   make baselines              Ejecutar notebook 02_baselines_tox21.ipynb
	@echo   make train-baselines        Entrenar RF / MLP / SMILES2vec (CLI)
	@echo   make train-baselines-verbose  Idem con logs detallados
	@echo.
	@echo   === JIC — GNN-GIN (Fase III) ===
	@echo   make train-gin              Entrenar GIN (requiere prepare-graphs)
	@echo   make train-gin-cv           5-fold CV scaffold
	@echo   make train-gin-verbose      Entrenamiento con logs por epoca
	@echo   make train-gin-wandb        Entrenamiento + Weights ^& Biases
	@echo   make train-gin-all          prepare-graphs + train-gin
	@echo   make train-gin-notebook     Ejecutar notebook 04_gnn_training.ipynb
	@echo.
	@echo   === JIC — Visor GNN 3D + XAI (Fase IV, puerto $(VIZ_PORT)) ===
	@echo   make install-viz            pip install viz/requirements.txt
	@echo   make build-viz-corpus       Corpus JSON con modelo real (viz/data/)
	@echo   make build-viz-corpus-demo  Corpus demo sin modelo
	@echo   make setup-viz              install-viz + corpus demo
	@echo   make setup-viz-full         install-viz + corpus real
	@echo   make xai-demo               setup-viz (demo rapido)
	@echo   make xai-all                train-gin + setup-viz-full
	@echo   make viz-check              Verificar deps del visor GNN
	@echo   make viz                    Visor GNN http://$(VIZ_HOST):$(VIZ_PORT)
	@echo   make viz-lan                Visor en 0.0.0.0 (red local)
	@echo   make viz-prod               Visor sin auto-reload
	@echo   make test-viz-gnn           Smoke test app GNN (puerto $(VIZ_PORT))
	@echo.
	@echo   === JIC — Panama + reportes (Fase V) ===
	@echo   make build-panama-corpus    Corpus PubChem + grafos PyG
	@echo   make build-panama-corpus-fast  Idem sin descarga GHS
	@echo   make build-panama-corpus-graphs  Rebuild .pt desde CSV existente
	@echo   make explain-panama         XAI sobre corpus panameno
	@echo   make validate-ghs           Predicciones vs etiquetas GHS
	@echo   make generate-panama-report PDF reporte MIDA/MINSA
	@echo   make panama-predict         Corpus + predicciones
	@echo   make panama-all             Pipeline Fase V completo
	@echo.
	@echo   === Analisis — ChEMBL / datos (Fases 1-2) ===
	@echo   make setup-chembl           Descargar BD al volumen Docker + levantar servidor
	@echo   make chembl-server-up       Servidor HTTP ChEMBL http://127.0.0.1:8765
	@echo   make test-chembl            Verificar conexion al servidor
	@echo   make chembl-extract         Extraer CSVs de bioactividad
	@echo   make chembl-notebook        Ejecutar fase1_adquisicion.ipynb
	@echo   make chembl-all             setup-chembl + chembl-extract
	@echo.
	@echo   === Analisis — Pipeline y dashboard (Fases 3-5, puerto $(ANALISIS_VIZ_PORT)) ===
	@echo   make analisis-verify        Smoke test Flujo B (corpus estructural ~147 compuestos)
	@echo   make analisis-prepare-dashboard  JSON para dashboard analytics
	@echo   make analisis-prepare-dashboard-bundle  Idem + bundle cloud
	@echo   make analisis-test-dashboard     Smoke test viz analytics
	@echo   make analisis-viz           Dashboard ChEMBL http://127.0.0.1:$(ANALISIS_VIZ_PORT)
	@echo   make analisis-all           prepare-dashboard + test + verify
	@echo.
	@echo   === Pipelines combinados ===
	@echo   make viz-analytics-all      analisis-prepare-dashboard + analisis-test-dashboard
	@echo   make viz-jic                panama-predict + analisis-prepare-dashboard + tests
	@echo.
	@echo   Fase 6 geodatos: spec en $(ANALISIS_DIR)/docs/fases/fase6_geodatos.md (sin target make)
	@echo.

# ═══════════════════════════════════════════════════════════════════════════
# ENTORNO (comun)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: setup setup-analisis install-pyg-ext clean check-gin-gpu
setup:
	$(PYTHON_PS) -m venv $(VENV_DIR)
	"$(VENV_PYTHON)" -m pip install --upgrade pip
	"$(VENV_PYTHON)" -m pip install -r requirements.txt

setup-analisis:
	"$(VENV_PYTHON)" -m pip install -r "$(ANALISIS_DIR)/requirements.txt"

install-pyg-ext:
	"$(VENV_PYTHON)" -m pip install torch_scatter torch_sparse torch_cluster \
		-f https://data.pyg.org/whl/torch-2.6.0+cu124.html

clean:
ifeq ($(OS),Windows_NT)
	if exist $(VENV_DIR) $(RM_RF) $(VENV_DIR)
else
	$(RM_RF) $(VENV_DIR)
endif

check-gin-gpu:
	"$(VENV_PYTHON)" -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

# ═══════════════════════════════════════════════════════════════════════════
# JIC — Datos y baselines (Fases I-II)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: prepare-graphs powershell-extract-data-from-tox21 wsl-extract-data-from-tox21 eda baselines train-baselines train-baselines-verbose
prepare-graphs:
	"$(VENV_PYTHON)" scripts/fase1/prepare_tox21_graphs.py

powershell-extract-data-from-tox21: prepare-graphs
wsl-extract-data-from-tox21: prepare-graphs

eda:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/01_eda_tox21.ipynb

baselines:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/02_baselines_tox21.ipynb

train-baselines:
	"$(VENV_PYTHON)" scripts/fase2/train_baselines.py

train-baselines-verbose:
	"$(VENV_PYTHON)" scripts/fase2/train_baselines.py -v

# ═══════════════════════════════════════════════════════════════════════════
# JIC — GNN-GIN (Fase III)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: train-gin train-gin-cv train-gin-verbose train-gin-wandb train-gin-all train-gin-all-verbose train-gin-notebook
train-gin:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG)

train-gin-cv:
	"$(VENV_PYTHON)" scripts/fase3/run_gin_cv.py --config $(CONFIG)

train-gin-verbose:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG) -v

train-gin-wandb:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG) -v --wandb

train-gin-all: prepare-graphs train-gin
train-gin-all-verbose: prepare-graphs train-gin-verbose

train-gin-notebook:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/04_gnn_training.ipynb

# ═══════════════════════════════════════════════════════════════════════════
# JIC — Visor GNN 3D + XAI (Fase IV)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: build-viz-corpus build-viz-corpus-demo setup-viz setup-viz-full xai-all xai-demo install-viz viz-check viz viz-serve viz-lan viz-prod test-viz-gnn
build-viz-corpus:
	"$(VENV_PYTHON)" scripts/fase4/build_viz_corpus.py

build-viz-corpus-demo:
	"$(VENV_PYTHON)" scripts/fase4/build_viz_corpus.py --demo

setup-viz: install-viz build-viz-corpus-demo
setup-viz-full: install-viz build-viz-corpus

xai-all: train-gin setup-viz-full
xai-demo: setup-viz

install-viz:
	"$(VENV_PYTHON)" -m pip install -r viz/requirements.txt

viz-check:
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --check-only

viz: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT) --reload

viz-serve: viz

viz-lan: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host 0.0.0.0 --port $(VIZ_PORT) --reload

viz-prod: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT)

test-viz-gnn:
	"$(VENV_PYTHON)" scripts/fase5/test_dashboard.py

# Alias legacy
test-viz-analytics: test-viz-gnn
test-dashboard: test-viz-gnn

# ═══════════════════════════════════════════════════════════════════════════
# JIC — Panama + reportes (Fase V)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: build-panama-corpus build-panama-corpus-fast build-panama-corpus-graphs explain-panama validate-ghs generate-panama-report panama-predict panama-all
build-panama-corpus:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py

build-panama-corpus-fast:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py --skip-ghs

build-panama-corpus-graphs:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py --skip-pubchem

explain-panama:
	"$(VENV_PYTHON)" scripts/fase5/explain_panama.py --model $(MODEL) --corpus $(PANAMA_CORPUS)

validate-ghs:
	"$(VENV_PYTHON)" scripts/fase5/validate_ghs.py \
		--predictions $(PANAMA_PREDICTIONS) \
		--ghs $(GHS_LABELS) \
		--output outputs/reports/ghs_validation.csv

generate-panama-report:
	"$(VENV_PYTHON)" scripts/fase5/generate_report.py \
		--results outputs/xai/ \
		--output outputs/reports/

panama-predict: build-panama-corpus explain-panama
panama-all: build-panama-corpus explain-panama validate-ghs generate-panama-report

# ═══════════════════════════════════════════════════════════════════════════
# ANALISIS — ChEMBL / datos (Fases 1-2)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: chembl-volume setup-chembl chembl-server-up chembl-server-down test-chembl chembl-extract chembl-notebook chembl-all

# Volumen nombrado (~30 GB tras setup). Idempotente: ignora error si ya existe.
chembl-volume:
	-docker volume create $(CHEMBL_VOLUME)

setup-chembl: chembl-volume
	$(CHEMBL_COMPOSE) build chembl-init
	$(CHEMBL_COMPOSE) --profile setup up --abort-on-container-exit chembl-init
	$(MAKE) chembl-server-up

chembl-server-up: chembl-volume
	$(CHEMBL_COMPOSE) build chembl-server
	$(CHEMBL_COMPOSE) up -d chembl-server

chembl-server-down:
	$(CHEMBL_COMPOSE) stop chembl-server

test-chembl: chembl-server-up
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase1/verify_chembl_db.py"

chembl-extract: test-chembl
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase1/extract_chembl.py" --config "$(ANALISIS_CONFIG)"

chembl-notebook:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace "$(CHEMBL_NOTEBOOK)"

chembl-all: setup-chembl chembl-extract

# ═══════════════════════════════════════════════════════════════════════════
# ANALISIS — Pipeline y dashboard (Fases 3-5)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: analisis-verify analisis-prepare-dashboard analisis-prepare-dashboard-bundle analisis-test-dashboard analisis-viz analisis-all
analisis-verify test-chembl-flow-b:
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase4/verify_flow_b.py"

analisis-prepare-dashboard prepare-dashboard:
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase5/prepare_dashboard.py"

analisis-prepare-dashboard-bundle prepare-dashboard-bundle:
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase5/prepare_dashboard.py" --bundle

analisis-test-dashboard:
	"$(VENV_PYTHON)" "$(ANALISIS_DIR)/scripts/fase5/test_dashboard.py"

analisis-viz:
	"$(VENV_PYTHON)" -m uvicorn viz.app:app --app-dir "$(ANALISIS_DIR)" --host $(VIZ_HOST) --port $(ANALISIS_VIZ_PORT) --reload

analisis-all: analisis-prepare-dashboard analisis-test-dashboard analisis-verify

# ═══════════════════════════════════════════════════════════════════════════
# Pipelines combinados
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: viz-analytics-all viz-jic dashboard-serve dashboard-all dashboard-jic
viz-analytics-all: analisis-prepare-dashboard analisis-test-dashboard

viz-jic: panama-predict analisis-prepare-dashboard test-viz-gnn analisis-test-dashboard

dashboard-serve: viz
dashboard-all: viz-analytics-all
dashboard-jic: viz-jic
