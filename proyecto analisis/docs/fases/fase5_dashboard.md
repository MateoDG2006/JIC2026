# Fase 5 — Dashboard Interactivo (Flujo C)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Integrar los resultados del analisis descriptivo/multivariado (Fases 2-4) en un dashboard web interactivo, sin ofrecer un predictor roto |
| **Duracion** | 3-5 dias |
| **Entradas** | `compounds_features.csv` (107 compuestos), `activities_clean.csv`, `outputs/chembl/results/clustering_summary.json`, `outputs/chembl/results/stats_tests.csv`, JSONs de artefactos, GeoJSON (parqueado) |
| **Salida** | Aplicacion FastAPI en `viz/` accesible en `http://127.0.0.1:8000` |
| **Rol lider** | ML Engineer |
| **Notebook** | `notebooks/fase5_dashboard.ipynb` |
| **Comando** | `make viz` |

---

## 1. Contexto y arquitectura

El dashboard unifica dos mundos:
- **Proyecto JIC (GNN):** Visualizacion 3D de moleculas, explicaciones XAI, predicciones Tox21 y comparativa GNN vs baselines. Estas paginas pertenecen al proyecto hermano (GNN + XAI) y se mantienen tal cual, pero deben quedar **claramente rotuladas como "Proyecto GNN"** para no confundirlas con el analisis descriptivo de este proyecto.
- **Proyecto de Analisis de Datos (ChEMBL):** EDA de los 107 compuestos, perfil de bioactividad/promiscuidad, PCA y clustering (Fase 4), y un **explorador de compuestos** individual. Ya **no incluye un predictor de pChEMBL**.

**Cambio de fondo respecto a la version anterior:** el dashboard ofrecia una pagina `/chembl/models` con metricas de clasificacion/regresion y un formulario de "prediccion pChEMBL interactiva" basado en `rf_regressor.pkl`. Ese modelo se evaluo con split por compuesto ([Fase 4 §12](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6)) y dio **R² negativo** (entre -0.25 y -1.13 segun el fold) — no generaliza a compuestos nuevos, porque los 8 descriptores moleculares son constantes por compuesto y el corpus tiene solo 107 moleculas distintas. Mostrar ese formulario como si produjera una prediccion util seria enganoso. **Se retira del dashboard por ese motivo** y se documenta el porque en la Fase 4 (baseline P6), no como producto del dashboard.

En su lugar, el dashboard suma un **Explorador de compuestos**: para cada uno de los 107 compuestos muestra su perfil fisicoquimico, su perfil de bioactividad/promiscuidad y el cluster que le asigno la Fase 4, con su posicion en el PCA. Es puramente descriptivo — no genera ninguna prediccion nueva.

La aplicacion sigue construida con **FastAPI** (backend Python) + **Plotly.js** (graficos interactivos) + **HTML/CSS** (templates). **No usa Dash** ni frameworks frontend como React: los graficos se renderizan con Plotly.js via CDN, las plantillas con Jinja2 y los datos llegan por endpoints JSON. La arquitectura tecnica (cache, rutas, `prepare_dashboard.py`) no cambia — lo que cambia es **que contenido se sirve**.

### Arranque rapido (vista de usuario)

```bash
make prepare-dashboard   # una vez, genera outputs/dashboard/*.json
make viz                 # http://127.0.0.1:8000
```

### Mapa de rutas resumido

| URL | Contenido | Proyecto |
|-----|-----------|---|
| `/` | Visor GNN 3D + corpus Panama | GNN |
| `/analytics/eda` | EDA de compuestos (107) — fisicoquimico + bioactividad | Analisis de datos |
| `/analytics/compounds` | Explorador de compuestos individual (perfil + cluster + PCA) | Analisis de datos |
| `/analytics/clusters` | PCA + clustering (Fase 4): silhouette, ARI vs familia | Analisis de datos |
| `/analytics/families` | Perfil por familia + tests estadisticos (Kruskal/Dunn) | Analisis de datos |
| `/panama/toxicity` | Heatmap 12 vias Tox21 + XAI | **GNN (proyecto hermano)** |
| `/panama/map` | Choropleth distritos Panama — **PARQUEADA** | GNN (parqueado, ver Fase 6) |
| `/panama/models` | Comparativa baselines vs GIN | **GNN (proyecto hermano)** |

### Arquitectura de directorios

```
viz/
├── app.py                  # Punto de entrada FastAPI (66 lineas)
├── config.py               # Constantes, nombres de tareas, labels (127 lineas)
├── routes/
│   ├── views.py            # Rutas HTML del proyecto JIC (GNN 3D)
│   ├── analytics.py        # Rutas HTML + API del proyecto de analisis (refactor: sin predictor)
│   └── api.py              # API REST general
├── services/
│   └── dashboard/
│       ├── cache.py         # Cache con invalidacion MD5 (50 lineas, sin cambios)
│       ├── artifacts.py     # Carga de CSVs y JSONs cacheados (87 lineas)
│       ├── compounds.py     # Explorador de compuestos — reemplaza a chembl.py (nueva funcion — a implementar)
│       └── xai.py           # Resolucion de figuras XAI (57 lineas, GNN)
├── templates/
│   ├── index.html           # Landing page
│   ├── eda.html             # EDA de compuestos (107) — fisicoquimico + bioactividad
│   ├── compounds.html       # Explorador de compuestos individual (nueva — a implementar)
│   ├── clusters.html        # PCA + clustering, silhouette, ARI (nueva — a implementar)
│   ├── families.html        # Perfil por familia + tests estadisticos (nueva — a implementar)
│   ├── panama_toxicity.html # Predicciones Tox21 por plaguicida (GNN)
│   ├── panama_map.html      # Mapa coropletico de Panama (GNN, PARQUEADA — ver Fase 6)
│   └── panama_models.html   # Comparacion GNN vs baselines (GNN)
└── static/
    ├── css/
    ├── js/
    └── data/                # Bundle de datos para el frontend
```

> **Nota:** `viz/services/dashboard/chembl.py` (el predictor `predict_pchembl`) se retira. Su reemplazo, `compounds.py`, expone funciones de solo lectura sobre `compounds_features.csv` y `clustering_summary.json` — nunca invoca `.predict()` de un modelo.

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

| Ruta | Template | Contenido | Proyecto |
|---|---|---|---|
| `/` | `index.html` | Landing con navegacion a ambos proyectos | — |
| `/analytics/eda` | `eda.html` | EDA de los 107 compuestos (fisicoquimico + bioactividad) | Analisis de datos |
| `/analytics/compounds` | `compounds.html` | Explorador de compuestos individual | Analisis de datos |
| `/analytics/clusters` | `clusters.html` | PCA + clustering, silhouette, ARI vs familia | Analisis de datos |
| `/analytics/families` | `families.html` | Perfil por familia + tests estadisticos | Analisis de datos |
| `/analytics/panama/toxicity` | `panama_toxicity.html` | Predicciones Tox21 por plaguicida | GNN (hermano) |
| `/analytics/panama/map` | `panama_map.html` | Mapa coropletico con Plotly — **PARQUEADA** | GNN (parqueado) |
| `/analytics/panama/models` | `panama_models.html` | Comparacion GIN vs baselines | GNN (hermano) |

### Endpoints API

| Endpoint | Metodo | Funcion |
|---|---|---|
| `/api/analytics/eda` | GET | Estadisticas de compuestos en JSON (nivel compuesto, 107) |
| `/api/analytics/compound-profile` | GET | Perfil completo de un compuesto: fisicoquimico + bioactividad + cluster + coordenadas PCA (nueva — a implementar) |
| `/api/analytics/clusters` | GET | Resultado de PCA + clustering: coordenadas, etiquetas de cluster, silhouette, ARI vs familia (nueva — a implementar) |
| `/api/analytics/family-stats` | GET | Estadisticos por familia + resultados de Kruskal-Wallis/Dunn (nueva — a implementar) |
| `/api/analytics/panama-map` | GET | GeoJSON + datos sociodemograficos — **PARQUEADA**, ver Fase 6 |
| `/api/analytics/model-comparison` | GET | Tabla comparativa GNN vs baselines Tox21 (proyecto hermano) |
| `/api/analytics/refresh` | POST | Invalidar cache (recarga datos) |
| `/xai/{filename}` | GET | SVGs de explicaciones XAI (proyecto hermano) |

> Se elimina `POST /api/analytics/predict` (predictor pChEMBL) y el endpoint `/api/analytics/model-evaluation` que exponia metricas de clasificacion/regresion ChEMBL rotas. Si se quiere mostrar el resultado del baseline honesto (Fase 4 §12, P6), debe hacerse en una seccion explicitamente rotulada "limite conocido — no usar como predictor", nunca como funcionalidad principal.

---

## 3. Sistema de cache (`viz/services/dashboard/cache.py`)

Sin cambios respecto al diseno original: el cache evita recargar CSVs grandes en cada request y usa checksums MD5 para invalidar automaticamente cuando los archivos cambian.

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

**Diferencia con `@lru_cache`:** El `lru_cache` solo invalida al reiniciar el servidor. El cache MD5 detecta cambios en disco automaticamente. Cachea `compounds_features.csv`, `activities_clean.csv` y `clustering_summary.json`.

---

## 4. Explorador de compuestos (`viz/services/dashboard/compounds.py`)

Reemplaza al antiguo `chembl.py` / `predict_pchembl`. **No predice nada** — agrega y sirve informacion ya calculada en las Fases 2-4.

```python
# viz/services/dashboard/compounds.py  (nueva funcion — a implementar)

def get_compound_profile(chembl_id: str) -> dict:
    """
    Arma el perfil descriptivo completo de un compuesto para el explorador.
    No invoca ningun modelo — solo lee y combina artefactos ya calculados.

    Fuentes:
        - data/processed/compounds_features.csv  -> perfil fisicoquimico
        - data/processed/activities_clean.csv    -> perfil de bioactividad
        - outputs/chembl/results/clustering_summary.json -> cluster asignado + coords PCA

    Retorna: {
        "chembl_id": "CHEMBL...",
        "compound_name": "...",
        "family": "Organophosphates",
        "fisicoquimico": {
            "mw_freebase": 350.0, "alogp": 3.5, "psa": 60.0,
            "hba": 4, "hbd": 1, "aromatic_rings": 2,
            "rtb": 5, "heavy_atoms": 22, "num_ro5_violations": 0,
        },
        "bioactividad": {
            "pchembl_median": 6.1, "pchembl_std": 0.8,
            "n_activities": 34, "n_targets": 4,
            "standard_type_distribution": {"IC50": 20, "Ki": 10, "Potency": 4},
            "pct_active": 0.62,
        },
        "cluster": {
            "cluster_id": 2,
            "pca_x": 1.34, "pca_y": -0.28,
            "coincide_con_family": True,
        },
    }
    """
    compounds_df = load_csv_cached("data/processed/compounds_features.csv")
    activities_df = load_csv_cached("data/processed/activities_clean.csv")
    clustering = load_json_cached("outputs/chembl/results/clustering_summary.json")
    # ... lookup y ensamblado del dict de arriba
```

**Por que se retira el predictor y no se repara:** el `RandomForestRegressor` de `rf_regressor.pkl` se entreno sobre 8 descriptores que son constantes dentro de cada compuesto (nunique=1 por `chembl_id`). Con split por fila el modelo parecia funcionar (R² ≈ 0.5-0.6) porque la misma molecula aparecia en train y test. Evaluado honestamente con split por compuesto ([Fase 4 §12](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6)), el R² en test es **negativo** (entre -0.25 y -1.13 segun el fold): el modelo no aprende una relacion generalizable entre estructura y potencia con esta featurizacion. Ofrecer un formulario de "prediccion" al usuario del dashboard implicaria una capacidad que el modelo no tiene. Esa limitacion es la motivacion del enfoque de grafos moleculares (GNN) del proyecto JIC; queda documentada en la Fase 4, no en el dashboard de cara al usuario.

---

## 5. Preparacion de artefactos (`scripts/fase5/prepare_dashboard.py`)

Este script genera los JSONs que el dashboard consume. Debe ejecutarse ANTES de levantar el servidor.

**Comando:** `make prepare-dashboard`

### Artefactos generados

| Archivo | Contenido | Consumido por |
|---|---|---|
| `viz/static/data/correlation.json` | Matriz Pearson + Spearman a nivel compuesto (107) | `/analytics/eda` |
| `viz/static/data/compounds_profile.json` | Perfil fisicoquimico + bioactividad por compuesto (107) | `/analytics/compounds` |
| `viz/static/data/pca_clusters.json` | Coordenadas PCA, etiquetas de cluster, silhouette, ARI vs familia | `/analytics/clusters` |
| `viz/static/data/family_stats.json` | Estadisticos por familia + resultados Kruskal-Wallis/Dunn | `/analytics/families` |
| `viz/static/data/xai_index.json` | Lista de figuras XAI disponibles (GNN) | `/analytics/panama/toxicity` |
| `viz/static/data/model_comparison.json` | Tabla comparativa GNN vs baselines Tox21 (GNN) | `/analytics/panama/models` |

> Se elimina `model_eval.json` (metricas ChEMBL clasificacion/regresion) y `predictor_defaults.json` (formulario del predictor retirado).

### Funciones principales

```python
def generate_correlation_json(compounds_csv_path, output_path):
    """Lee compounds_features.csv (107 filas), calcula Pearson+Spearman entre
    descriptores y pchembl_median, guarda JSON. Nivel compuesto — sin fuga."""

def generate_compounds_profile_json(compounds_csv_path, activities_csv_path, output_path):
    """Combina compounds_features.csv + activities_clean.csv en un registro
    por compuesto con perfil fisicoquimico y de bioactividad."""
    # (nueva funcion — a implementar)

def generate_pca_clusters_json(clustering_summary_path, output_path):
    """Lee outputs/chembl/results/clustering_summary.json (Fase 4) y lo
    reformatea para el scatter interactivo (coords PCA + cluster + familia)."""
    # (nueva funcion — a implementar)

def generate_family_stats_json(stats_tests_csv_path, compounds_csv_path, output_path):
    """Lee outputs/chembl/results/stats_tests.csv (Kruskal/Dunn) + agregados
    por familia desde compounds_features.csv."""
    # (nueva funcion — a implementar)

def generate_xai_index(figures_dir, output_path):
    """Lista todos los SVGs en outputs/xai/figures/ con metadata. (GNN)"""

def generate_model_comparison(results_dir, output_path):
    """Combina gin_results.csv + baseline_results.csv en tabla unificada. (GNN)"""

def bundle_all(output_dir):
    """Ejecuta todas las funciones anteriores."""
```

---

## 6. Rutas de analytics (`viz/routes/analytics.py`)

### Rutas HTML

```python
@router.get("/eda", response_class=HTMLResponse)
async def eda_page(request: Request):
    """EDA de los 107 compuestos — fisicoquimico + bioactividad."""
    df = load_csv_cached("data/processed/compounds_features.csv")
    stats = summary_stats(df)
    return templates.TemplateResponse("eda.html", {
        "request": request,
        "stats": stats,
        "n_compounds": len(df),
        "n_activities": load_csv_cached("data/processed/activities_clean.csv").shape[0],
    })


@router.get("/compounds", response_class=HTMLResponse)
async def compounds_page(request: Request):
    """Explorador de compuestos individual — sin prediccion."""
    df = load_csv_cached("data/processed/compounds_features.csv")
    return templates.TemplateResponse("compounds.html", {
        "request": request,
        "compound_list": df[["chembl_id", "compound_name", "family"]].to_dict("records"),
    })


@router.get("/clusters", response_class=HTMLResponse)
async def clusters_page(request: Request):
    """PCA + clustering de la Fase 4."""
    summary = load_json_cached("outputs/chembl/results/clustering_summary.json")
    return templates.TemplateResponse("clusters.html", {
        "request": request,
        "silhouette": summary.get("silhouette"),
        "ari_vs_family": summary.get("ari_vs_family"),
        "k": summary.get("k"),
    })
```

### Endpoints API

```python
@router.get("/api/analytics/eda")
async def api_eda():
    """JSON con estadisticas de compuestos (107) para graficos Plotly."""
    df = load_csv_cached("data/processed/compounds_features.csv")
    return {
        "distributions": compute_distributions(df),
        "family_stats": compute_family_stats(df),
    }

@router.get("/api/analytics/compound-profile")
async def api_compound_profile(chembl_id: str):
    """Perfil descriptivo de un compuesto (fisicoquimico + bioactividad + cluster)."""
    return get_compound_profile(chembl_id)

@router.get("/api/analytics/clusters")
async def api_clusters():
    """Coordenadas PCA + etiquetas de cluster + metricas de validacion."""
    return load_json_cached("viz/static/data/pca_clusters.json")

@router.post("/api/analytics/refresh")
async def api_refresh():
    """Invalida cache y recarga datos desde disco."""
    invalidate_all()
    return {"status": "cache invalidated"}
```

> El endpoint `POST /api/analytics/predict` desaparece por completo: no hay reemplazo con la misma firma porque ya no se ofrece prediccion en el dashboard de este proyecto.

---

## 7. Configuracion del dashboard (`viz/config.py`)

### Constantes principales

```python
TASK_NAMES = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]  # Proyecto GNN — Tox21

TASK_DESCRIPTIONS = {
    "NR-AR": "Receptor de androgenos",
    "NR-AhR": "Receptor aril-hidrocarburo",
    # ...
}  # Proyecto GNN — Tox21

MAP_VARIABLES = {
    "pop_density": "Densidad poblacional (hab/km²)",
    "ag_fraction": "Fraccion agricola (%)",
    "poverty_index": "Indice de pobreza",
    "exposure_risk": "Riesgo de exposicion",
}  # PARQUEADA — ver Fase 6, se mantiene solo por referencia de codigo

FEATURE_LABELS = {
    "mw_freebase": "Peso molecular (Da)",
    "alogp": "LogP (lipofilicidad)",
    "psa": "Area de superficie polar (Å²)",
    # ...
}  # Analisis de datos — descriptores de compounds_features.csv

CLUSTER_LABELS = {
    # etiquetas descriptivas de cada cluster una vez identificados (Fase 4)
}  # (nueva constante — a implementar)
```

---

## 8. Trabajo por rol

### ML Engineer (LIDER)

| # | Tarea | Archivo | Detalle |
|---|---|---|---|
| 1 | Implementar app.py | `viz/app.py` | Montar routers y archivos estaticos (sin cambios) |
| 2 | Implementar sistema de cache | `viz/services/dashboard/cache.py` | Cache MD5 (sin cambios) |
| 3 | Implementar explorador de compuestos | `viz/services/dashboard/compounds.py` | `get_compound_profile`, sin `.predict()` (reemplaza a `chembl.py`) |
| 4 | Implementar rutas analytics | `viz/routes/analytics.py` | EDA, explorador, clusters, familias — sin endpoint de prediccion |
| 5 | Generar artefactos JSON | `scripts/fase5/prepare_dashboard.py` | `compounds_profile.json`, `pca_clusters.json`, `family_stats.json`, `correlation.json` |
| 6 | Implementar resolucion XAI | `viz/services/dashboard/xai.py` | Servir SVGs de explicaciones (proyecto hermano, sin cambios) |
| 7 | Configurar constantes | `viz/config.py` | Nombres de tareas GNN, labels descriptores, `CLUSTER_LABELS` |
| 8 | Templates HTML | `viz/templates/*.html` | `compounds.html`, `clusters.html`, `families.html` nuevos; retirar formulario de prediccion de `eda.html`/antiguo `models.html` |
| 9 | Estilos CSS + JS | `viz/static/` | Interactividad frontend (scatter PCA, tabla de compuestos filtrable) |
| 10 | Tests | `make test-viz-analytics` | Verificar endpoints; el smoke test de `predict` se reemplaza por el de `compound-profile` |

### Ingeniero de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Verificar que los CSVs existen | Confirmar `compounds_features.csv` y `activities_clean.csv` (Fase 2) |
| Verificar artefactos de Fase 4 | Confirmar `clustering_summary.json` y `stats_tests.csv` |
| Verificar cache | Probar que el cache invalida al modificar un CSV |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Revisar visualizaciones EDA | Verificar que los graficos Plotly (histogramas, boxplots, PCA) son correctos a nivel compuesto |
| Proponer mejoras de UI | Feedback sobre colores, labels, layout del explorador de compuestos |

### Cientifico de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar explorador de compuestos | Confirmar que `compound-profile` no expone ninguna prediccion, solo datos agregados |
| Verificar metricas mostradas | Confirmar que silhouette/ARI/tests coinciden con los artefactos de la Fase 4 |
| Verificar rotulado del proyecto GNN | Confirmar que `/panama/toxicity` y `/panama/models` estan claramente marcadas como proyecto hermano |

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

# 4. Probar el explorador de compuestos (reemplaza al smoke test del predictor)
curl "http://127.0.0.1:8000/api/analytics/compound-profile?chembl_id=CHEMBL1234"

# 5. Probar clusters/PCA
curl http://127.0.0.1:8000/api/analytics/clusters

# 6. Invalidar cache
curl -X POST http://127.0.0.1:8000/api/analytics/refresh

# 7. Ejecutar tests
make test-viz-analytics
```

### Comandos Makefile relevantes

| Target | Descripcion |
|--------|-------------|
| `make viz` | Servidor unico (GNN + analisis de datos) |
| `make prepare-dashboard` | Genera JSON derivados en `outputs/dashboard/` |
| `make test-viz-analytics` | Smoke test del dashboard analitico (incluye `compound-profile`, ya no `predict`) |
| `make viz-analytics-all` | prepare-dashboard + test (mapa geo: ver spec Fase 6) |
| `make viz-jic` | panama-predict + prepare-dashboard + test |

Los alias `make dashboard-serve` y `make test-dashboard` redirigen a los targets equivalentes de `viz/` por compatibilidad con documentacion previa.

---

## 10. Paginas del dashboard

### `/analytics/eda` — EDA de compuestos

| Componente | Tipo Plotly | Datos |
|---|---|---|
| Histogramas de descriptores | `Plotly.newPlot` (histogram) | `compounds_features.csv` (107 compuestos) |
| Boxplots por familia | `Plotly.newPlot` (box) | `compounds_features.csv` — anotar n por familia |
| Heatmap de correlacion | `Plotly.newPlot` (heatmap) | `correlation.json` (Pearson + Spearman, nivel compuesto) |
| Tabla de estadisticas | HTML table | `summary_statistics` sobre `compounds_features.csv` |
| Distribucion de `standard_type` | `Plotly.newPlot` (bar) | `activities_clean.csv` |

### `/analytics/compounds` — Explorador de compuestos

| Componente | Tipo | Datos |
|---|---|---|
| Selector de compuesto | Dropdown/buscador HTML | `compounds_profile.json` |
| Perfil fisicoquimico | Tabla + radar Plotly | descriptores del compuesto seleccionado |
| Perfil de bioactividad/promiscuidad | Barras Plotly (`n_targets`, `pchembl_median`, distribucion de `standard_type`) | `activities_clean.csv` agregado |
| Cluster asignado | Texto + marcador resaltado en el scatter de `/analytics/clusters` | `pca_clusters.json` |

> Esta pagina reemplaza al antiguo formulario de "Prediccion pChEMBL interactiva". No hay ningun input del usuario que dispare un `.predict()` — solo lookup de un compuesto existente.

### `/analytics/clusters` — PCA y clustering (Fase 4)

| Componente | Tipo | Datos |
|---|---|---|
| Scatter PCA (PC1 vs PC2) coloreado por cluster | `Plotly.newPlot` (scatter) | `pca_clusters.json` |
| Scatter PCA coloreado por familia (comparacion) | `Plotly.newPlot` (scatter) | `pca_clusters.json` |
| Metricas de validacion | Tabla HTML | silhouette, ARI vs familia, k elegido (`clustering_summary.json`) |
| Nota metodologica | Texto | recuerda que los clusters son un patron descriptivo, no una prediccion |

### `/analytics/families` — Perfil por familia

| Componente | Tipo | Datos |
|---|---|---|
| Boxplots anotados de potencia por familia | `Plotly.newPlot` (box) | `family_stats.json` — anotar n por familia (compuesto) |
| Tabla de tests estadisticos | HTML table | `stats_tests.csv` (Kruskal-Wallis + post-hoc Dunn + tamano de efecto) |
| Aviso de tamano de muestra | Texto | advertencia explicita para familias con n bajo (p. ej. Carbamates, Triazines) |

### `/analytics/panama/toxicity` — Predicciones Tox21 (proyecto GNN — hermano)

| Componente | Tipo | Datos |
|---|---|---|
| Selector de plaguicida | Dropdown HTML | `xai_index.json` |
| Perfil de 12 dianas | Plotly radar/bar | predicciones del modelo GIN |
| Molecula coloreada por XAI | SVG incrustado | `outputs/xai/figures/` |

> Rotular visualmente esta pagina (banner o badge) como parte del **proyecto GNN + XAI**, distinto del analisis descriptivo ChEMBL de este documento.

### `/analytics/panama/map` — Mapa de Panama — **PARQUEADA**

Retirada del flujo principal del dashboard hasta contar con un dataset de uso/registro de plaguicidas por distrito (ver Fase 6 — Geodatos, estado PARQUEADA). El codigo (`panama_map.html`, `MAP_VARIABLES`, endpoint `/api/analytics/panama-map`) se mantiene en el repositorio como referencia pero no debe enlazarse desde la navegacion principal ni el articulo.

### `/analytics/panama/models` — Comparacion GNN vs Baselines (proyecto GNN — hermano)

| Componente | Tipo | Datos |
|---|---|---|
| Tabla de AUC por tarea | HTML table | `model_comparison.json` |
| Grafico de barras | Plotly grouped bar | `model_comparison.json` |

---

## 11. Criterios de exito

- [ ] `make viz` levanta el servidor sin errores
- [ ] `/health` retorna `{"status": "ok"}`
- [ ] Las paginas de analisis de datos (`/analytics/eda`, `/analytics/compounds`, `/analytics/clusters`, `/analytics/families`) cargan correctamente
- [ ] `/api/analytics/compound-profile` retorna perfil fisicoquimico + bioactividad + cluster para cualquiera de los 107 compuestos, sin invocar ningun `.predict()`
- [ ] El scatter de PCA/clusters es interactivo y coincide con `clustering_summary.json` (silhouette, ARI, k)
- [ ] La pagina de familias muestra n por grupo junto a cada boxplot (nunca un boxplot sin contexto de tamano de muestra)
- [ ] No existe ningun endpoint ni formulario que ofrezca una "prediccion de toxicidad/potencia" en el dashboard de este proyecto
- [ ] El cache invalida al modificar un CSV
- [ ] Las paginas `/analytics/panama/toxicity` y `/analytics/panama/models` estan rotuladas visualmente como proyecto GNN (hermano)
- [ ] `/analytics/panama/map` no aparece en la navegacion principal (PARQUEADA)
- [ ] Las figuras XAI se sirven correctamente como SVG
- [ ] `make test-viz-analytics` pasa

---

## 12. Troubleshooting

| Problema | Causa | Solucion |
|---|---|---|
| `ModuleNotFoundError: viz` | No esta en el PYTHONPATH | Ejecutar desde la raiz del proyecto |
| `FileNotFoundError: compounds_features.csv` | No se ejecuto Fase 2 (refactor de dos tablas) | Ejecutar `notebooks/fase2_limpieza.ipynb` completo |
| `FileNotFoundError: activities_clean.csv` | Idem — falta la tabla de mediciones dedup | Ejecutar Fase 2 completa |
| `FileNotFoundError: clustering_summary.json` | No se ejecuto Fase 4 (PCA + clustering) | Ejecutar `notebooks/fase4_modelado.ipynb` |
| `JSONDecodeError` en artefactos | No se ejecuto `prepare_dashboard` | `make prepare-dashboard` |
| El explorador muestra "compuesto no encontrado" | `chembl_id` no existe en `compounds_features.csv` (107 posibles) | Verificar el id contra la lista de `compound_list` |
| Puerto 8000 ocupado | Otro proceso usa el puerto | `uvicorn viz.app:app --port 8001` |
| Aparece un formulario de prediccion en algun template viejo | Cache de navegador o template no actualizado | Purgar `viz/templates/eda.html`/`models.html` antiguos, confirmar que `compounds.py` reemplazo a `chembl.py` |
| Mapa no renderiza | Fase 6 no implementada — falta dataset geográfico con trazabilidad | Ver [Fase 6 — spec futura](fase6_geodatos.md); `/panama/map` requiere `outputs/dashboard/panama_distritos.geojson` |
| Cache no actualiza | Checksum identico | `POST /api/analytics/refresh` |

---

*Fase anterior:* [Fase 4 — Analisis multivariado y contraste de hipotesis](fase4_modelado.md)
*Siguiente fase:* [Fase 6 — Geodatos (spec futura)](fase6_geodatos.md)
