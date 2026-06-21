"""Aplicación FastAPI unificada del proyecto: visor GNN 3D + analytics ChEMBL/Panamá.

Estructura:
    /                        → visor GNN 3D (vistas Jinja2)
    /eda, /chembl/models     → analytics ChEMBL (EDA, modelos)
    /panama/{toxicity,map}   → análisis Panamá (toxicidad, mapa)
    /panama/models           → comparativa baselines vs GIN (AUDIT P9)
    /api/*                   → REST: predicción GIN, XAI, propiedades
    /api/analytics/*         → REST: datos EDA, métricas, geo, comparativa
    /api/analytics/refresh   → POST: invalida caché si artefactos cambiaron en disco (P3)
    /xai/<filename>          → SVGs precomputados (GNNExplainer/Grad-CAM)
    /health                  → estado del servidor (P12)
    /static/*                → CSS, JS, imágenes
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from viz.config import STATIC_DIR
from viz.routes.analytics import router as analytics_router
from viz.routes.api import router as api_router
from viz.routes.views import router as views_router
from viz.services.dashboard.xai import xai_figures_dir

app = FastAPI(
    title="GNN-Tox Viewer",
    description="Visor GNN-GIN/XAI + analytics ChEMBL y Panamá",
    version="0.2.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(views_router)
app.include_router(analytics_router)
app.include_router(api_router)


@app.get("/xai/{filename}")
def serve_xai_svg(filename: str):
    """Sirve figuras XAI precomputadas desde ``outputs/xai/figures/``.

    Solo acepta archivos SVG. Útil para incrustar explicaciones GNNExplainer/Grad-CAM
    en las plantillas Jinja2 sin tener que regenerarlas en cada petición.
    """
    directory = xai_figures_dir()
    path = directory / filename
    if not path.is_file() or path.suffix.lower() != ".svg":
        raise HTTPException(404, "Figura XAI no encontrada")
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/health")
def health_check():
    """Health check para deployment cloud (Render/Docker) — AUDIT P12.

    Devuelve filas de ChEMBL, número de compuestos del perfil de toxicidad
    y si el modelo GIN está disponible. Permite probes de Kubernetes/Render.
    """
    from viz.services.dashboard.artifacts import load_chembl, load_toxicity_profile
    from viz.services import inference

    try:
        chembl_rows = len(load_chembl())
    except Exception:
        chembl_rows = -1
    try:
        tox_rows = len(load_toxicity_profile())
    except Exception:
        tox_rows = -1

    return {
        "status": "ok",
        "chembl_rows": chembl_rows,
        "toxicity_compounds": tox_rows,
        "gin_model_available": inference.model_available(),
    }


if __name__ == "__main__":
    import uvicorn

    from viz.config import viz_host, viz_port

    uvicorn.run("viz.app:app", host=viz_host(), port=viz_port(), reload=True)
