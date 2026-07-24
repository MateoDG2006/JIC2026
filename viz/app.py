"""Aplicación FastAPI del visor GNN 3D + XAI (proyecto JIC).

Estructura:
    /                        → landing del proyecto
    /visor                   → corpus Panamá + buscador PubChem/SMILES
    /molecule/{id}, /analyze → predicción en vivo + XAI
    /api/*                   → REST: predicción GIN, XAI, propiedades, PubChem
    /xai/<filename>          → SVGs precomputados (GNNExplainer/Grad-CAM)
    /health                  → estado del servidor
    /static/*                → CSS, JS, imágenes

Analytics ChEMBL viven en ``proyecto analisis/viz/`` (puerto 8001).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from viz.config import STATIC_DIR
from viz.routes.api import router as api_router
from viz.routes.views import router as views_router
from viz.services.dashboard import xai_figures_dir

app = FastAPI(
    title="GNN-Tox Viewer",
    description="Visor GNN-GIN/XAI (analytics ChEMBL → proyecto analisis/viz/)",
    version="0.2.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(views_router)
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
    """Health check GNN — analytics ChEMBL en ``proyecto analisis/viz/``."""
    from viz.services import inference

    try:
        from viz.services.corpus import list_compounds

        tox_rows = len(list_compounds())
    except Exception:
        tox_rows = -1

    return {
        "status": "ok",
        "toxicity_compounds": tox_rows,
        "gin_model_available": inference.model_available(),
        "analytics_app": "proyecto analisis/viz/app.py",
    }


if __name__ == "__main__":
    import uvicorn

    from viz.config import viz_host, viz_port

    uvicorn.run("viz.app:app", host=viz_host(), port=viz_port(), reload=True)
