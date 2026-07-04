"""Rutas HTML y API JSON del dashboard de análisis ChEMBL (Fases 2–4)."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.paths import setup_path

setup_path()

from viz.config import NUMERIC_COLS, TEMPLATES_DIR
from viz.services.dashboard.artifacts import (
    load_baseline_honest,
    load_chembl,
    load_compounds_potency,
    load_correlation,
    load_family_stats,
    load_pca_clusters,
)
from viz.services.dashboard.cache import invalidate_all

router = APIRouter(tags=["analytics"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _filter_chembl(
    family: str | None,
    mw_min: float | None,
    mw_max: float | None,
) -> pd.DataFrame:
    df = load_chembl().copy()
    if family and family != "ALL":
        df = df[df["family"] == family]
    if mw_min is not None:
        df = df[df["mw_freebase"] >= mw_min]
    if mw_max is not None:
        df = df[df["mw_freebase"] <= mw_max]
    return df


@router.get("/eda", response_class=HTMLResponse)
def page_eda(request: Request):
    """EDA: histogramas, boxplots, correlación y scatter de compuestos."""
    return templates.TemplateResponse(request, "analytics_exploration.html", {"active_nav": "eda"})


@router.get("/api/analytics/chembl/meta")
def chembl_meta():
    df = load_chembl()
    numeric = [c for c in NUMERIC_COLS if c in df.columns]
    return {
        "numeric_cols": numeric,
        "families": sorted(df["family"].dropna().unique().tolist()),
        "mw_min": float(df["mw_freebase"].min()),
        "mw_max": float(df["mw_freebase"].max()),
        "mw_default": [
            float(df["mw_freebase"].quantile(0.05)),
            float(df["mw_freebase"].quantile(0.95)),
        ],
    }


@router.get("/api/analytics/chembl/data")
def chembl_data(
    variable: str = Query("pchembl_median_binding"),
    family: str = Query("ALL"),
    mw_min: float | None = Query(None),
    mw_max: float | None = Query(None),
):
    df = _filter_chembl(family, mw_min, mw_max)
    if variable not in df.columns:
        if variable == "pchembl_median_binding":
            df = load_compounds_potency().copy()
            if family and family != "ALL":
                df = df[df["family"] == family]
            if mw_min is not None:
                df = df[df["mw_freebase"] >= mw_min]
            if mw_max is not None:
                df = df[df["mw_freebase"] <= mw_max]
        if variable not in df.columns:
            raise HTTPException(400, f"Variable desconocida: {variable}")

    scatter_cols = [
        c
        for c in (
            "mw_freebase",
            "alogp",
            "compound_name",
            "pchembl_median_binding",
            "pchembl_std_binding",
            "reliability_tier",
            "target_inestable",
        )
        if c in df.columns
    ]

    return {
        "variable": variable,
        "histogram": df[variable].dropna().tolist(),
        "boxplot": {
            "family": df["family"].tolist(),
            "values": df[variable].tolist(),
        },
        "scatter": df[scatter_cols].replace({pd.NA: None}).to_dict(orient="records"),
        "count": len(df),
    }


@router.get("/api/analytics/chembl/correlation")
def chembl_correlation():
    return load_correlation()


@router.get("/api/analytics/baseline/honest")
def baseline_honest():
    """Métricas del baseline predictivo honesto (Fase 4 §4)."""
    return load_baseline_honest()


@router.get("/api/analytics/clusters/pca")
def clusters_pca():
    """Coordenadas PCA + resumen de clustering (Fase 4 §2)."""
    return load_pca_clusters()


@router.get("/api/analytics/families/stats")
def families_stats():
    """Tests Kruskal y conteos por familia (Fase 4 §3)."""
    return load_family_stats()


@router.post("/api/analytics/refresh")
def refresh_data_cache():
    invalidate_all()
    return {"status": "ok", "message": "Cache invalidado"}
