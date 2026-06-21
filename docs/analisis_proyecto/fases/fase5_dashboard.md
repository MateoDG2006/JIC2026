# Fase 5 — Dashboard Interactivo (Flujo C)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Integrar resultados de analisis y modelos en un dashboard web interactivo |
| **Duracion** | 3-5 dias |
| **Entradas** | `chembl_clean.csv`, modelos `.pkl`, JSONs de artefactos, GeoJSON |
| **Salida** | Aplicacion FastAPI en `viz/` accesible en `http://127.0.0.1:8000` |
| **Rol lider** | ML Engineer |
| **Notebook** | `notebooks/proyecto analisis de datos/fase5_dashboard.ipynb` |
| **Comando** | `make viz` |

---

## 1. Contexto y arquitectura

El dashboard unifica dos mundos:
- **Proyecto JIC (GNN):** Visualizacion 3D de moleculas, explicaciones XAI, predicciones Tox21
- **Proyecto de Analisis de Datos (ChEMBL):** EDA interactivo, metricas de modelos, prediccion pChEMBL, mapa Panama

La aplicacion esta construida con **FastAPI** (backend Python) + **Plotly.js** (graficos interactivos) + **HTML/CSS** (templates). **No usa Dash** ni frameworks frontend como React: los graficos se renderizan con Plotly.js via CDN, las plantillas con Jinja2 y los datos llegan por endpoints JSON.

### Arranque rapido (vista de usuario)

```bash
make prepare-dashboard   # una vez, genera outputs/dashboard/*.json
make viz                 # http://127.0.0.1:8000
```

### Mapa de rutas resumido

| URL | Contenido |
|-----|-----------|
| `/` | Visor GNN 3D + corpus Panama |
| `/eda` | Exploracion ChEMBL (Plotly.js) |
| `/chembl/models` | Modelos sklearn + predictor pChEMBL |
| `/panama/toxicity` | Heatmap 12 vias Tox21 + XAI |
| `/panama/map` | Choropleth distritos Panama |
| `/panama/models` | Comparativa baselines vs GIN |

### Arquitectura de directorios

```
viz/
├── app.py                  # Punto de entrada FastAPI (66 lineas)
├── config.py               # Constantes, nombres de tareas, labels (127 lineas)
├── routes/
│   ├── views.py            # Rutas HTML del proyecto JIC (GNN 3D)
│   ├── analytics.py        # Rutas HTML + API del proyecto de analisis (293 lineas)
│   └── api.py              # API REST general
├── services/
│   └── dashboard/
│       ├── cache.py         # Cache con invalidacion MD5 (50 lineas)
│       ├── artifacts.py     # Carga de CSVs y JSONs cacheados (87 lineas)
│       ├── chembl.py        # Predictor pChEMBL con RF (37 lineas)
│       └── xai.py           # Resolucion de figuras XAI (57 lineas)
├── templates/
│   ├── index.html           # Landing page
│   ├── eda.html             # Dashboard EDA ChEMBL
│   ├── models.html          # Metricas de modelos ChEMBL
│   ├── panama_toxicity.html # Predicciones Tox21 por plaguicida
│   ├── panama_map.html      # Mapa coropletico de Panama
│   └── panama_models.html   # Comparacion modelos RF vs SVM
└── static/
    ├── css/
    ├── js/
    └── data/                # Bundle de datos para el frontend
```

---

## 2. Aplicacion FastAPI (`viz/app.py`)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from viz.routes import views, analytics, api

app = FastAPI(title="GNN Toxicity Panama — Dashboard")

app.include_router(views.router)
app.include_router(analytics.router, prefix="/analytics")
app.include_router(api.router, prefix="/api")

app.mount("/static", StaticFiles(directory="viz/static"), name="static")
app.mount("/xai", StaticFiles(directory="outputs/xai/figures"), name="xai")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Rutas principales

| Ruta | Template | Contenido |
|---|---|---|
| `/` | `index.html` | Landing con navegacion a ambos proyectos |
| `/analytics/eda` | `eda.html` | Dashboard EDA interactivo |
| `/analytics/chembl/models` | `models.html` | Metricas de clasificacion y regresion |
| `/analytics/panama/toxicity` | `panama_toxicity.html` | Predicciones Tox21 por plaguicida |
| `/analytics/panama/map` | `panama_map.html` | Mapa coropletico con Plotly |
| `/analytics/panama/models` | `panama_models.html` | Comparacion RF vs SVM |

### Endpoints API

| Endpoint | Metodo | Funcion |
|---|---|---|
| `/api/analytics/eda` | GET | Datos EDA en JSON |
| `/api/analytics/correlation` | GET | Matriz de correlacion |
| `/api/analytics/model-evaluation` | GET | Metricas de todos los modelos |
| `/api/analytics/predict` | POST | Prediccion pChEMBL interactiva |
| `/api/analytics/panama-map` | GET | GeoJSON + datos sociodemograficos |
| `/api/analytics/model-comparison` | GET | Tabla comparativa modelos |
| `/api/analytics/refresh` | POST | Invalidar cache (recarga datos) |
| `/xai/{filename}` | GET | SVGs de explicaciones XAI |

---

## 3. Sistema de cache (`viz/services/dashboard/cache.py`)

El cache evita recargar CSVs grandes en cada request. Usa checksums MD5 para invalidar automaticamente cuando los archivos cambian.

```python
import hashlib
from pathlib import Path
import pandas as pd
import json

_cache: dict[str, tuple[str, any]] = {}

def _checksum(path: Path) -> str:
    """MD5 del archivo — cambia si el contenido cambia."""
    return hashlib.md5(path.read_bytes()).hexdigest()

def load_csv_cached(path: str | Path) -> pd.DataFrame:
    """Carga CSV con cache por checksum MD5."""
    p = Path(path)
    key = str(p)
    cs = _checksum(p)
    if key in _cache and _cache[key][0] == cs:
        return _cache[key][1]
    df = pd.read_csv(p)
    _cache[key] = (cs, df)
    return df

def load_json_cached(path: str | Path) -> dict:
    """Carga JSON con cache por checksum MD5."""
    p = Path(path)
    key = str(p)
    cs = _checksum(p)
    if key in _cache and _cache[key][0] == cs:
        return _cache[key][1]
    data = json.loads(p.read_text(encoding="utf-8"))
    _cache[key] = (cs, data)
    return data

def invalidate_all():
    """Limpia todo el cache — usado por POST /api/analytics/refresh."""
    _cache.clear()
```

**Diferencia con `@lru_cache`:** El `lru_cache` solo invalida al reiniciar el servidor. El cache MD5 detecta cambios en disco automaticamente.

---

## 4. Predictor interactivo (`viz/services/dashboard/chembl.py`)

```python
import joblib
import numpy as np
from pathlib import Path

_rf_model = None

def load_rf_regressor():
    """Carga el RF Regressor una vez (lazy singleton)."""
    global _rf_model
    if _rf_model is None:
        model_path = Path("outputs/chembl/models/rf_regressor.pkl")
        if model_path.exists():
            _rf_model = joblib.load(model_path)
    return _rf_model

def predict_pchembl(user_inputs: dict) -> dict:
    """
    Predice pChEMBL a partir de descriptores moleculares del usuario.
    
    user_inputs: {
        "mw_freebase": 350.0,
        "alogp": 3.5,
        "psa": 60.0,
        "hba": 4,
        "hbd": 1,
        ...
    }
    
    Retorna: {
        "pchembl_predicted": 5.23,
        "activity_class": "Inactive",
        "confidence_note": "..."
    }
    """
    model = load_rf_regressor()
    if model is None:
        return {"error": "Modelo no disponible"}
    
    feature_order = [
        "mw_freebase", "alogp", "psa", "hba", "hbd",
        "aromatic_rings", "heavy_atoms", "rtb", "num_ro5_violations",
    ]
    X = np.array([[user_inputs.get(f, 0) for f in feature_order]])
    pred = model.predict(X)[0]
    
    return {
        "pchembl_predicted": round(pred, 3),
        "activity_class": "Active" if pred >= 6.0 else "Inactive",
        "confidence_note": "Prediccion basada en descriptores moleculares globales",
    }
```

---

## 5. Preparacion de artefactos (`scripts/fase5/prepare_dashboard.py`)

Este script genera los JSONs que el dashboard consume. Debe ejecutarse ANTES de levantar el servidor.

**Comando:** `make prepare-dashboard`

### Artefactos generados

| Archivo | Contenido | Consumido por |
|---|---|---|
| `viz/static/data/correlation.json` | Matriz Pearson + Spearman | `/analytics/eda` |
| `viz/static/data/model_eval.json` | Metricas de clasificacion y regresion | `/analytics/chembl/models` |
| `viz/static/data/predictor_defaults.json` | Valores default para el formulario | `/api/analytics/predict` |
| `viz/static/data/xai_index.json` | Lista de figuras XAI disponibles | `/analytics/panama/toxicity` |
| `viz/static/data/model_comparison.json` | Tabla comparativa GNN vs baselines | `/analytics/panama/models` |

### Funciones principales (378 lineas)

```python
def generate_correlation_json(csv_path, output_path):
    """Lee chembl_clean.csv, calcula Pearson+Spearman, guarda JSON."""

def generate_model_eval_json(metrics_path, output_path):
    """Lee metrics_summary.csv, estructura como JSON para graficos."""

def generate_predictor_defaults(csv_path, output_path):
    """Calcula medianas de features para pre-llenar el formulario."""

def generate_xai_index(figures_dir, output_path):
    """Lista todos los SVGs en outputs/xai/figures/ con metadata."""

def generate_model_comparison(results_dir, output_path):
    """Combina gin_results.csv + baseline_results.csv en tabla unificada."""

def bundle_all(output_dir):
    """Ejecuta todas las funciones anteriores."""
```

---

## 6. Rutas de analytics (`viz/routes/analytics.py`)

### Rutas HTML (5)

```python
@router.get("/eda", response_class=HTMLResponse)
async def eda_page(request: Request):
    """Dashboard EDA interactivo con Plotly.js"""
    df = load_csv_cached("data/processed/chembl_clean.csv")
    stats = summary_stats(df)
    return templates.TemplateResponse("eda.html", {
        "request": request,
        "stats": stats,
        "n_compounds": df["chembl_id"].nunique(),
        "n_records": len(df),
    })
```

### Endpoints API (10)

```python
@router.get("/api/analytics/eda")
async def api_eda():
    """JSON con estadisticas para graficos Plotly."""
    df = load_csv_cached("data/processed/chembl_clean.csv")
    return {
        "distributions": compute_distributions(df),
        "class_balance": compute_class_balance(df),
        "family_stats": compute_family_stats(df),
    }

@router.post("/api/analytics/predict")
async def api_predict(inputs: dict):
    """Prediccion interactiva de pChEMBL."""
    result = predict_pchembl(inputs)
    return result

@router.post("/api/analytics/refresh")
async def api_refresh():
    """Invalida cache y recarga datos desde disco."""
    invalidate_all()
    return {"status": "cache invalidated"}
```

---

## 7. Configuracion del dashboard (`viz/config.py`)

### Constantes principales

```python
TASK_NAMES = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

TASK_DESCRIPTIONS = {
    "NR-AR": "Receptor de androgenos",
    "NR-AhR": "Receptor aril-hidrocarburo",
    # ...
}

MAP_VARIABLES = {
    "pop_density": "Densidad poblacional (hab/km²)",
    "ag_fraction": "Fraccion agricola (%)",
    "poverty_index": "Indice de pobreza",
    "exposure_risk": "Riesgo de exposicion",
}

FEATURE_LABELS = {
    "mw_freebase": "Peso molecular (Da)",
    "alogp": "LogP (lipofilicidad)",
    "psa": "Area de superficie polar (Å²)",
    # ...
}
```

---

## 8. Trabajo por rol

### ML Engineer (LIDER)

| # | Tarea | Archivo | Detalle |
|---|---|---|---|
| 1 | Implementar app.py | `viz/app.py` | Montar routers y archivos estaticos |
| 2 | Implementar sistema de cache | `viz/services/dashboard/cache.py` | Cache MD5 |
| 3 | Implementar predictor | `viz/services/dashboard/chembl.py` | Carga RF + prediccion |
| 4 | Implementar rutas analytics | `viz/routes/analytics.py` | 5 HTML + 10 API endpoints |
| 5 | Generar artefactos JSON | `scripts/fase5/prepare_dashboard.py` | 5 JSONs para frontend |
| 6 | Implementar resolucion XAI | `viz/services/dashboard/xai.py` | Servir SVGs de explicaciones |
| 7 | Configurar constantes | `viz/config.py` | Nombres de tareas, labels, variables mapa |
| 8 | Templates HTML | `viz/templates/*.html` | 6 paginas con Plotly.js |
| 9 | Estilos CSS + JS | `viz/static/` | Interactividad frontend |
| 10 | Tests | `make test-viz-analytics` | Verificar endpoints |

### Ingeniero de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Verificar que los CSVs existen | Confirmar `chembl_clean.csv` y `metrics_summary.csv` |
| Preparar GeoJSON | Ejecutar `scripts/analisis_proyecto/fase6/02_download_geodata.py` |
| Verificar cache | Probar que el cache invalida al modificar un CSV |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Revisar visualizaciones EDA | Verificar que los graficos Plotly son correctos |
| Proponer mejoras de UI | Feedback sobre colores, labels, layout |

### Cientifico de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar predictor | Probar endpoint `/api/analytics/predict` con valores conocidos |
| Verificar metricas mostradas | Confirmar que coinciden con `metrics_summary.csv` |

---

## 9. Ejecucion

```bash
# 1. Generar artefactos JSON (prerequisito)
make prepare-dashboard

# 2. Levantar servidor de desarrollo
make viz
# -> http://127.0.0.1:8000

# 3. Verificar health
curl http://127.0.0.1:8000/health

# 4. Probar prediccion
curl -X POST http://127.0.0.1:8000/api/analytics/predict \
     -H "Content-Type: application/json" \
     -d '{"mw_freebase": 350, "alogp": 3.5, "psa": 60, "hba": 4, "hbd": 1, "aromatic_rings": 2, "heavy_atoms": 22, "rtb": 5, "num_ro5_violations": 0}'

# 5. Invalidar cache
curl -X POST http://127.0.0.1:8000/api/analytics/refresh

# 6. Ejecutar tests
make test-viz-analytics
```

### Comandos Makefile relevantes

| Target | Descripcion |
|--------|-------------|
| `make viz` | Servidor unico (GNN + analytics) |
| `make prepare-dashboard` | Genera JSON derivados en `outputs/dashboard/` |
| `make test-viz-analytics` | Smoke test del dashboard analitico |
| `make viz-analytics-all` | geodata + prepare-dashboard + test |
| `make viz-jic` | panama-predict + prepare-dashboard + test |

Los alias `make dashboard-serve` y `make test-dashboard` redirigen a los targets equivalentes de `viz/` por compatibilidad con documentacion previa.

---

## 10. Paginas del dashboard

### `/analytics/eda` — EDA Interactivo

| Componente | Tipo Plotly | Datos |
|---|---|---|
| Histogramas de descriptores | `Plotly.newPlot` (histogram) | chembl_clean.csv |
| Boxplots por familia | `Plotly.newPlot` (box) | chembl_clean.csv |
| Heatmap de correlacion | `Plotly.newPlot` (heatmap) | correlation.json |
| Tabla de estadisticas | HTML table | summary_statistics |
| Balance de clases | `Plotly.newPlot` (pie) | chembl_clean.csv |

### `/analytics/chembl/models` — Metricas de Modelos

| Componente | Tipo | Datos |
|---|---|---|
| Tabla comparativa | HTML table | model_eval.json |
| Barras de metricas | Plotly bar | model_eval.json |
| Nota sobre split | Texto | Hardcoded |

### `/analytics/panama/toxicity` — Predicciones Tox21

| Componente | Tipo | Datos |
|---|---|---|
| Selector de plaguicida | Dropdown HTML | xai_index.json |
| Perfil de 12 dianas | Plotly radar/bar | predicciones del modelo GIN |
| Molecula coloreada por XAI | SVG incrustado | outputs/xai/figures/ |

### `/analytics/panama/map` — Mapa de Panama

| Componente | Tipo | Datos |
|---|---|---|
| Mapa coropletico | Plotly choropleth | GeoJSON + geodata |
| Selector de variable | Dropdown | MAP_VARIABLES |
| Tabla de provincias | HTML table | geodata |

### `/analytics/panama/models` — Comparacion GNN vs Baselines

| Componente | Tipo | Datos |
|---|---|---|
| Tabla de AUC por tarea | HTML table | model_comparison.json |
| Grafico de barras | Plotly grouped bar | model_comparison.json |

---

## 11. Criterios de exito

- [ ] `make viz` levanta el servidor sin errores
- [ ] `/health` retorna `{"status": "ok"}`
- [ ] Las 5 paginas de analytics cargan correctamente
- [ ] El predictor retorna valores coherentes (pChEMBL entre 3 y 10)
- [ ] El cache invalida al modificar un CSV
- [ ] Los graficos Plotly son interactivos (hover, zoom)
- [ ] El mapa de Panama renderiza las 10 provincias
- [ ] Las figuras XAI se sirven correctamente como SVG
- [ ] `make test-viz-analytics` pasa

---

## 12. Troubleshooting

| Problema | Causa | Solucion |
|---|---|---|
| `ModuleNotFoundError: viz` | No esta en el PYTHONPATH | Ejecutar desde la raiz del proyecto |
| `FileNotFoundError: chembl_clean.csv` | No se ejecuto Fase 2 | `make chembl-extract` + ejecutar notebook |
| `FileNotFoundError: rf_regressor.pkl` | No se ejecuto Fase 4 | Ejecutar Secciones 4-5 del notebook |
| `JSONDecodeError` en artefactos | No se ejecuto prepare_dashboard | `make prepare-dashboard` |
| Puerto 8000 ocupado | Otro proceso usa el puerto | `uvicorn viz.app:app --port 8001` |
| Mapa no renderiza | Falta GeoJSON | `python scripts/analisis_proyecto/fase6/02_download_geodata.py` |
| Cache no actualiza | Checksum identico | `POST /api/analytics/refresh` |

---

*Fase anterior:* [Fase 4 — Modelado supervisado](fase4_modelado.md)  
*Siguiente fase:* [Fase 6 — Geodatos de Panama](fase6_geodatos.md)
