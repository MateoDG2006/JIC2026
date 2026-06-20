# Analytics web — integrado en `viz/` (FastAPI)

## Arranque

```bash
make prepare-dashboard   # una vez, genera outputs/dashboard/*.json
make viz                 # http://127.0.0.1:8000
```

## Rutas

| URL | Contenido |
|-----|-----------|
| `/` | Visor GNN 3D + corpus Panamá |
| `/eda` | Exploración ChEMBL (Plotly.js) |
| `/chembl/models` | Modelos sklearn + predictor pChEMBL |
| `/panama/toxicity` | Heatmap 12 vías Tox21 + XAI |
| `/panama/map` | Choropleth distritos Panamá |

## Arquitectura

```
viz/
├── app.py                      # FastAPI unificado
├── config.py                   # Rutas outputs/ + data/processed/
├── routes/analytics.py         # HTML + API /api/analytics/*
├── services/dashboard/         # Carga artefactos + inferencia sklearn
├── templates/analytics_*.html
└── static/js/analytics_*.js    # Plotly.js vía CDN
```

**Sin Dash.** Gráficos con Plotly.js; plantillas Jinja2; APIs JSON para datos.

## Comandos Makefile

| Target | Descripción |
|--------|-------------|
| `make viz` | Servidor único (GNN + analytics) |
| `make prepare-dashboard` | JSON derivados en `outputs/dashboard/` |
| `make test-viz-analytics` | Smoke test |
| `make viz-analytics-all` | geodata + prepare + test |
| `make viz-jic` | panama-predict + prepare + test |

Los alias `make dashboard-serve` y `make test-dashboard` redirigen a los targets de `viz/`.
