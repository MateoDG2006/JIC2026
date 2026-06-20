"""Rutas HTML y API JSON para analytics ChEMBL + Panamá (sin Dash)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from viz.config import (
    FEATURE_LABELS,
    MAP_VARIABLES,
    NUMERIC_COLS,
    PREDICTOR_NOTE,
    TASK_NAMES,
    TEMPLATES_DIR,
)
from viz.services.dashboard.artifacts import load_model_comparison
from viz.services.dashboard.cache import invalidate_all
from viz.services.dashboard import (
    geojson_to_dataframe,
    load_chembl,
    load_correlation,
    load_feature_cols,
    load_geojson,
    load_metrics_summary,
    load_model_eval,
    load_toxicity_profile,
    predict_pchembl,
    resolve_xai_filename,
)

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


# ── Vistas HTML ───────────────────────────────────────────────────────────


@router.get("/eda", response_class=HTMLResponse)
def page_eda(request: Request):
    return templates.TemplateResponse(request, "analytics_exploration.html", {"active_nav": "eda"})


@router.get("/chembl/models", response_class=HTMLResponse)
def page_models(request: Request):
    metrics = load_metrics_summary()
    rf = metrics[metrics["modelo"] == "RandomForest"].iloc[0]
    return templates.TemplateResponse(
        request,
        "analytics_models.html",
        {
            "active_nav": "models",
            "feature_cols": load_feature_cols(),
            "feature_labels": FEATURE_LABELS,
            "r2_test": float(rf["r2_test"]),
            "predictor_note": PREDICTOR_NOTE,
        },
    )


@router.get("/panama/toxicity", response_class=HTMLResponse)
def page_toxicity(request: Request):
    df = load_toxicity_profile()
    return templates.TemplateResponse(
        request,
        "analytics_toxicity.html",
        {
            "active_nav": "toxicity",
            "families": sorted(df["familia"].dropna().unique().tolist()),
            "alerts": sorted(df["alerta"].dropna().unique().tolist()),
            "task_names": TASK_NAMES,
        },
    )


@router.get("/panama/map", response_class=HTMLResponse)
def page_map(request: Request):
    return templates.TemplateResponse(
        request,
        "analytics_map.html",
        {"active_nav": "map", "map_variables": MAP_VARIABLES},
    )


# ── API JSON ──────────────────────────────────────────────────────────────


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
    variable: str = Query("pchembl_value"),
    family: str = Query("ALL"),
    mw_min: float | None = Query(None),
    mw_max: float | None = Query(None),
):
    df = _filter_chembl(family, mw_min, mw_max)
    if variable not in df.columns:
        raise HTTPException(400, f"Variable desconocida: {variable}")

    scatter_cols = ["mw_freebase", "alogp", "activity_class", "compound_name", "pchembl_value"]
    scatter_cols = [c for c in scatter_cols if c in df.columns]

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


@router.get("/api/analytics/models/eval")
def models_eval():
    return load_model_eval()


@router.get("/api/analytics/models/features")
def models_features():
    return {"feature_cols": load_feature_cols(), "labels": FEATURE_LABELS}


class PredictRequest(BaseModel):
    inputs: dict[str, float] = Field(default_factory=dict)


@router.post("/api/analytics/models/predict")
def models_predict(req: PredictRequest):
    try:
        pred = predict_pchembl(req.inputs)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    level = "ALTO" if pred >= 6 else "MODERADO" if pred >= 5 else "BAJO"
    return {"pchembl": round(pred, 2), "level": level}


@router.get("/api/analytics/toxicity/profile")
def toxicity_profile(
    family: str = Query("ALL"),
    alerta: str = Query("ALL"),
    limit: int = Query(40, ge=1, le=100),
):
    df = load_toxicity_profile().copy()
    if family != "ALL":
        df = df[df["familia"] == family]
    if alerta != "ALL":
        df = df[df["alerta"] == alerta]

    df = df.sort_values("prob_max", ascending=False).head(limit)
    tasks = [t for t in TASK_NAMES if t in df.columns]

    compounds = []
    for _, row in df.iterrows():
        compounds.append({
            "compuesto": row["compuesto"],
            "familia": row.get("familia"),
            "alerta": row.get("alerta"),
            "tarea_critica": row.get("tarea_critica"),
            "prob_max": float(row["prob_max"]),
            "tasks": {t: float(row[t]) for t in tasks},
        })

    return {"tasks": tasks, "compounds": compounds}


@router.get("/api/analytics/toxicity/xai")
def toxicity_xai(
    compound: str = Query(...),
    method: str = Query("gnnexplainer"),
):
    row = load_toxicity_profile()
    match = row[row["compuesto"] == compound]
    if match.empty:
        raise HTTPException(404, f"Compuesto no encontrado: {compound}")

    info = match.iloc[0]
    task = str(info.get("tarea_critica", "SR-ARE"))
    filename = resolve_xai_filename(compound, task, method)
    if not filename:
        raise HTTPException(404, f"No hay SVG XAI ({method}) para {compound}")

    return {
        "compound": compound,
        "task": task,
        "method": method,
        "url": f"/xai/{filename}",
        "prob_max": float(info["prob_max"]),
        "alerta": str(info["alerta"]),
    }


@router.get("/panama/models", response_class=HTMLResponse)
def page_model_comparison(request: Request):
    return templates.TemplateResponse(
        request,
        "analytics_comparison.html",
        {"active_nav": "comparison"},
    )


@router.post("/api/analytics/refresh")
def refresh_data_cache():
    """Invalida caches — recarga artefactos si cambiaron en disco (AUDIT P3)."""
    invalidate_all()
    return {"status": "ok", "message": "Cache invalidado"}


@router.get("/api/analytics/models/comparison")
def models_comparison():
    return load_model_comparison()


@router.get("/api/analytics/metrics/summary")
def metrics_summary_api():
    df = load_metrics_summary()
    return df.replace({pd.NA: None}).to_dict(orient="records")


@router.get("/api/analytics/geo")
def geo_data():
    geo = load_geojson()
    geo["_meta"] = {
        "disclaimer": (
            "Datos sociodemográficos: estimaciones geográficas reproducibles "
            "(fuente: estimacion_geografica_inec_mapi). No son datos oficiales "
            "descargados del INEC. Sustituir por MAPI cuando esté disponible."
        ),
    }
    return geo


@router.get("/api/analytics/geo/summary")
def geo_summary(variable: str = Query("superficie_agricola_ha")):
    if variable not in MAP_VARIABLES:
        raise HTTPException(400, f"Variable desconocida: {variable}")

    df = geojson_to_dataframe()
    if variable not in df.columns:
        raise HTTPException(400, f"Columna ausente en geojson: {variable}")

    prov = (
        df.groupby("provincia", as_index=False)[variable]
        .sum()
        .sort_values(variable, ascending=False)
    )
    return {
        "variable": variable,
        "label": MAP_VARIABLES[variable],
        "districts": df[["shapeName", "nombre_distrito", "provincia", variable]].replace({pd.NA: None}).to_dict(orient="records"),
        "provinces": prov.replace({pd.NA: None}).to_dict(orient="records"),
    }
