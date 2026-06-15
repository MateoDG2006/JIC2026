"""Aplicacion FastAPI para visualizacion 3D de toxicidad molecular."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from viz.config import STATIC_DIR
from viz.routes.api import router as api_router
from viz.routes.views import router as views_router

app = FastAPI(
    title="GNN-Tox Viewer",
    description="Visualizacion 3D interactiva de predicciones de toxicidad con XAI",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(api_router)
app.include_router(views_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("viz.app:app", host="127.0.0.1", port=8000, reload=True)
