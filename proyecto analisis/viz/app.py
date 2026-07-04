"""Visor FastAPI — Proyecto Análisis de Datos (ChEMBL / Panamá)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.paths import setup_path

setup_path()

from viz.config import STATIC_DIR  # noqa: E402
from viz.routes.analytics import router as analytics_router  # noqa: E402

app = FastAPI(
    title="ChEMBL Analytics — Proyecto Análisis",
    description="EDA, multivariado y explorador de compuestos (107 plaguicidas)",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(analytics_router)


@app.get("/health")
def health_check():
    from viz.services.dashboard.artifacts import load_chembl

    try:
        rows = len(load_chembl())
    except Exception:
        rows = -1
    return {"status": "ok", "project": "proyecto analisis", "compound_rows": rows}


if __name__ == "__main__":
    import uvicorn

    from viz.config import viz_host, viz_port

    uvicorn.run("viz.app:app", host=viz_host(), port=viz_port(), reload=True)
