# Dashboard migrado a `viz/`

El dashboard ya no usa Dash. Vive integrado en el visor FastAPI:

- **Código:** `viz/routes/analytics.py`, `viz/services/dashboard/`, `viz/templates/analytics_*.html`
- **Arranque:** `make viz` → http://127.0.0.1:8000
- **Rutas:**
  - `/` — Visor GNN 3D
  - `/eda` — Exploración ChEMBL
  - `/chembl/models` — Modelos sklearn
  - `/panama/toxicity` — Heatmap GNN + XAI
  - `/panama/map` — Mapa Panamá

La carpeta `dashboard/data/` es legacy y puede eliminarse.
