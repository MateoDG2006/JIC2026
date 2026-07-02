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
	"$(VENV_PYTHON)" scripts/fase1/prepare_tox21_graphs.py

powershell-extract-data-from-tox21: prepare-graphs

wsl-extract-data-from-tox21: prepare-graphs

eda:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/01_eda_tox21.ipynb

# ── Baselines (Fase II) ───────────────────────────────────────────────────

baselines:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/02_baselines_tox21.ipynb

train-baselines:
	"$(VENV_PYTHON)" scripts/fase2/train_baselines.py

train-baselines-verbose:
	"$(VENV_PYTHON)" scripts/fase2/train_baselines.py -v

# ── GNN-GIN (Fase III) ────────────────────────────────────────────────────
# Requisito: make prepare-graphs (genera data/processed/graphs_*.pt)

train-gin:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG)

train-gin-cv:
	"$(VENV_PYTHON)" scripts/fase3/run_gin_cv.py --config $(CONFIG)

train-gin-verbose:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG) -v

train-gin-wandb:
	"$(VENV_PYTHON)" scripts/fase3/train_gin.py --config $(CONFIG) -v --wandb

# Pipeline completo: grafos + entrenamiento GIN
train-gin-all: prepare-graphs train-gin

train-gin-all-verbose: prepare-graphs train-gin-verbose

check-gin-gpu:
	"$(VENV_PYTHON)" -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

train-gin-notebook:
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace notebooks/04_gnn_training.ipynb

# ── Rutas compartidas (Fases IV–V) ─────────────────────────────────────────

MODEL := outputs/models/best_gin_model.pt
PANAMA_CORPUS := data/processed/panama_corpus.pt
PANAMA_PREDICTIONS := outputs/results/panama_predictions.csv
GHS_LABELS := data/raw/pubchem_ghs_labels.csv

# ── XAI + visor (Fase IV) ─────────────────────────────────────────────────
# Corpus: predicciones + GNNExplainer + Grad-CAM → viz/data/*.json
# Requisito corpus real: make train-gin (genera $(MODEL))
# Sin modelo: make xai-demo  →  make viz

build-viz-corpus:
	"$(VENV_PYTHON)" scripts/fase4/build_viz_corpus.py

build-viz-corpus-demo:
	"$(VENV_PYTHON)" scripts/fase4/build_viz_corpus.py --demo

setup-viz: install-viz build-viz-corpus-demo

setup-viz-full: install-viz build-viz-corpus

xai-all: train-gin setup-viz-full

xai-demo: setup-viz

VIZ_HOST := 127.0.0.1
VIZ_PORT := 8000

install-viz:
	"$(VENV_PYTHON)" -m pip install -r viz/requirements.txt

viz-check:
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --check-only

# Visor unificado: GNN 3D + analytics ChEMBL/Panamá (solo FastAPI)
viz: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT) --reload

viz-serve: viz

# Acceso desde otros dispositivos en la misma red (puerto 8000 por defecto)
viz-lan: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host 0.0.0.0 --port $(VIZ_PORT) --reload

# Servidor sin auto-reload (mas estable en demos/presentaciones)
viz-prod: viz-check
	"$(VENV_PYTHON)" scripts/fase4/viz_serve.py --host $(VIZ_HOST) --port $(VIZ_PORT)

# ── Panamá (Fase V) ────────────────────────────────────────────────────────
# Corpus desde PubChem → predicciones → validación GHS → reporte MIDA/MINSA
# Requisito inferencia: make train-gin + make build-panama-corpus

build-panama-corpus:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py

# Omite descarga GHS (más rápido; útil para iterar sobre grafos)
build-panama-corpus-fast:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py --skip-ghs

# Reconstruye panama_corpus.pt desde CSV existente (sin llamar a PubChem)
build-panama-corpus-graphs:
	"$(VENV_PYTHON)" scripts/fase5/build_panama_corpus.py --skip-pubchem

# Predicciones multitarea + explicaciones XAI sobre el corpus panameño
explain-panama:
	"$(VENV_PYTHON)" scripts/fase5/explain_panama.py --model $(MODEL) --corpus $(PANAMA_CORPUS)

# Correlaciona predicciones del modelo con etiquetas GHS de PubChem
validate-ghs:
	"$(VENV_PYTHON)" scripts/fase5/validate_ghs.py \
		--predictions $(PANAMA_PREDICTIONS) \
		--ghs $(GHS_LABELS) \
		--output outputs/reports/ghs_validation.csv

# Reporte interpretado para actores institucionales (MIDA/MINSA)
generate-panama-report:
	"$(VENV_PYTHON)" scripts/fase5/generate_report.py \
		--results outputs/xai/ \
		--output outputs/reports/

# Corpus + predicciones (sin validación GHS ni reporte PDF)
panama-predict: build-panama-corpus explain-panama

# Pipeline Fase V completo
panama-all: build-panama-corpus explain-panama validate-ghs generate-panama-report

# ── ChEMBL local — Flujo A (análisis de datos, corpus MIDA) ───────────────
# BD persistente en volumen Docker ``jic2026_chembl_db`` (~5 GB descarga + ~15 GB instalada)
#   make chembl-docker-up        → build + descarga ChEMBLdb al volumen (una vez)
#   make chembl-docker-import    → copia BD existente en data/external/chembl/ al volumen
#   make test-chembl-docker      → verifica BD dentro del contenedor
#   make chembl-extract-docker   → extracción CSV vía contenedor (sin copiar BD al host)
#   make chembl-sync-host        → copia volumen → data/external/chembl/ (scripts locales)
#   make test-chembl             → verifica BD en host (requiere chembl-sync-host)
#   make chembl-extract          → extracción CSV en host (requiere chembl-sync-host)

CHEMBL_COMPOSE := docker compose -f docker/docker-compose.yml
CHEMBL_VOLUME := jic2026_chembl_db
CHEMBL_HOST_DIR := data/external/chembl
CHEMBL_DB := $(CHEMBL_HOST_DIR)/chembl_37.db
CHEMBL_NOTEBOOK := notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb

chembl-docker-build:
	$(CHEMBL_COMPOSE) build chembl-init

chembl-docker-build-app:
	$(CHEMBL_COMPOSE) build toxgnn

# Levanta Docker y guarda chembl_37.db en el volumen nombrado (idempotente)
chembl-docker-up: chembl-docker-build chembl-docker-build-app
	$(CHEMBL_COMPOSE) --profile setup up --abort-on-container-exit chembl-init

chembl-docker-down:
	$(CHEMBL_COMPOSE) --profile setup down --remove-orphans

# Migra una BD ya descargada en data/external/chembl/ al volumen Docker
chembl-docker-import: chembl-docker-build
	$(CHEMBL_COMPOSE) --profile setup run --rm --entrypoint "" \
		-v "$(CURDIR)/$(CHEMBL_HOST_DIR):/import:ro" \
		chembl-init \
		sh -c 'if [ -f /data/chembl/chembl_37.db ]; then echo "[chembl-import] Volumen ya tiene chembl_37.db"; \
		elif [ -f /import/chembl_37.db ]; then cp -a /import/. /data/chembl/ && echo "[chembl-import] Copiado al volumen $(CHEMBL_VOLUME)"; \
		else echo "[chembl-import] No hay BD en $(CHEMBL_HOST_DIR)/ ni en el volumen"; exit 1; fi'

setup-chembl: chembl-docker-up

test-chembl-docker: chembl-docker-build-app
	$(CHEMBL_COMPOSE) run --rm toxgnn python scripts/analisis_proyecto/fase1/verify_chembl_db.py

# Copia volumen → host (solo si falta chembl_37.db local; ~15 GB)
chembl-sync-host: chembl-docker-build-app
ifeq ($(OS),Windows_NT)
	if not exist "$(CHEMBL_HOST_DIR)" mkdir "$(CHEMBL_HOST_DIR)"
else
	mkdir -p $(CHEMBL_HOST_DIR)
endif
	$(CHEMBL_COMPOSE) run --rm --no-deps --entrypoint "" \
		-v "$(CURDIR)/$(CHEMBL_HOST_DIR):/host" \
		toxgnn \
		sh -c 'if [ ! -f /data/chembl/chembl_37.db ]; then echo "Volumen vacío — ejecuta make chembl-docker-up"; exit 1; fi; \
		if [ -f /host/chembl_37.db ]; then echo "Host ya tiene chembl_37.db — omitiendo copia"; \
		else cp /data/chembl/chembl_37.db /data/chembl/manifest.json /host/ && echo "Copiado a $(CHEMBL_HOST_DIR)/"; fi'

test-chembl: chembl-sync-host
	"$(VENV_PYTHON)" scripts/analisis_proyecto/fase1/verify_chembl_db.py

chembl-extract: test-chembl
	"$(VENV_PYTHON)" scripts/analisis_proyecto/fase1/extract_chembl_local.py --config $(CONFIG)

chembl-extract-api:
	"$(VENV_PYTHON)" scripts/analisis_proyecto/fase1/extract_chembl_local.py --config $(CONFIG) --backend api

chembl-extract-docker: chembl-docker-build-app test-chembl-docker
	$(CHEMBL_COMPOSE) run --rm toxgnn

chembl-notebook: test-chembl
	"$(VENV_PYTHON)" -m jupyter nbconvert --execute --to notebook --inplace "$(CHEMBL_NOTEBOOK)"

test-chembl-flow-b:
	"$(VENV_PYTHON)" scripts/analisis_proyecto/fase4/verify_flow_b.py

chembl-all: setup-chembl chembl-extract-docker

# ── Geodatos Panamá (Flujo D) ───────────────────────────────────────────────
download-geodata:
	"$(VENV_PYTHON)" scripts/analisis_proyecto/fase6/02_download_geodata.py

# ── Analytics integrado en viz/ (FastAPI + Plotly.js) ───────────────────────
prepare-dashboard:
	"$(VENV_PYTHON)" scripts/fase5/prepare_dashboard.py

prepare-dashboard-bundle:
	"$(VENV_PYTHON)" scripts/fase5/prepare_dashboard.py --bundle

test-viz-analytics:
	"$(VENV_PYTHON)" scripts/fase5/test_dashboard.py

# Alias de compatibilidad
test-dashboard: test-viz-analytics
dashboard-serve: viz
dashboard-all: viz-analytics-all
dashboard-jic: viz-jic

# Pipeline completo analytics
viz-analytics-all: download-geodata prepare-dashboard test-viz-analytics

# Pipeline JIC: predicciones GNN + artefactos analytics
viz-jic: panama-predict prepare-dashboard test-viz-analytics

.PHONY: setup install-pyg-ext clean prepare-graphs powershell-extract-data-from-tox21 wsl-extract-data-from-tox21 eda baselines train-baselines train-baselines-verbose train-gin train-gin-cv train-gin-verbose train-gin-wandb train-gin-all train-gin-all-verbose check-gin-gpu train-gin-notebook build-viz-corpus build-viz-corpus-demo setup-viz setup-viz-full xai-all xai-demo install-viz viz-check viz viz-serve viz-lan viz-prod build-panama-corpus build-panama-corpus-fast build-panama-corpus-graphs explain-panama validate-ghs generate-panama-report panama-predict panama-all panama-notebook chembl-docker-build chembl-docker-build-app chembl-docker-up chembl-docker-down chembl-docker-import setup-chembl test-chembl test-chembl-docker chembl-sync-host chembl-extract chembl-extract-api chembl-extract-docker chembl-notebook test-chembl-flow-b chembl-all download-geodata prepare-dashboard prepare-dashboard-bundle test-viz-analytics test-dashboard dashboard-serve dashboard-all dashboard-jic viz-analytics-all viz-jic
