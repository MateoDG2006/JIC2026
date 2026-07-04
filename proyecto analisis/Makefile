# Makefile — Proyecto Análisis de Datos (ChEMBL)
# Ejecutar desde: proyecto analisis/

PYTHON ?= python
CONFIG := config/config.yaml
CHEMBL_HOST_DIR := data/external/chembl
CHEMBL_COMPOSE := docker compose -f docker/docker-compose.yml

.PHONY: verify outputs viz test-dashboard prepare-dashboard download-geodata chembl-extract

verify:
	$(PYTHON) scripts/fase4/verify_flow_b.py

outputs:
	$(PYTHON) scripts/run_opcion_a_outputs.py

viz:
	$(PYTHON) -m uvicorn viz.app:app --app-dir . --host 127.0.0.1 --port 8001 --reload

test-dashboard:
	$(PYTHON) scripts/fase5/test_dashboard.py

prepare-dashboard:
	$(PYTHON) scripts/fase5/prepare_dashboard.py

download-geodata:
	$(PYTHON) scripts/fase6/02_download_geodata.py

chembl-extract:
	$(PYTHON) scripts/fase1/extract_chembl_local.py --config $(CONFIG)

chembl-docker-up:
	$(CHEMBL_COMPOSE) --profile setup up --abort-on-container-exit chembl-init
