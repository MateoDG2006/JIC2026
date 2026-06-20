"""Aplicacion FastAPI unificada: visor GNN 3D + analytics ChEMBL/Panama."""

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
    """Sirve figuras XAI precomputadas desde outputs/xai/figures/."""
    directory = xai_figures_dir()
    path = directory / filename
    if not path.is_file() or path.suffix.lower() != ".svg":
        raise HTTPException(404, "Figura XAI no encontrada")
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/health")
def health_check():
    """Health check para deployment (AUDIT P12)."""
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
