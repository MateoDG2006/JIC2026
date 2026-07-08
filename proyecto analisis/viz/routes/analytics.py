"""Rutas HTML y API JSON del dashboard de análisis ChEMBL (Fases 2–4)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.paths import PROJECT_ROOT, setup_path

setup_path()

from viz.config import ARTIFACTS_DIR, NUMERIC_COLS, RESULTS_DIR, TEMPLATES_DIR
from viz.glossary import payload as glossary_payload
from viz.services.dashboard.artifacts import (
    load_activities,
    load_baseline_honest,
    load_chembl,
    load_compounds_potency,
    load_correlation,
    load_family_stats,
    load_pca_clusters,
)
from viz.services.dashboard.cache import invalidate_all


def _read_json_any(name: str) -> dict:
    """Lee un JSON de outputs/dashboard o de outputs/chembl/results."""
    for base in (ARTIFACTS_DIR, RESULTS_DIR):
        p = base / name
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _records(df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame a lista de dicts segura para JSON (NaN/inf → null)."""
    safe = df.copy()
    numeric_cols = safe.select_dtypes(include=[np.number]).columns
    if len(numeric_cols):
        safe[numeric_cols] = safe[numeric_cols].replace([np.inf, -np.inf], np.nan)
    safe = safe.astype(object).where(pd.notna(safe), None)
    return json.loads(safe.to_json(orient="records"))

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


@router.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    """Interfaz única (SPA): todas las fases en una sola pantalla con navegación animada."""
    return templates.TemplateResponse(request, "dashboard.html", {"active_nav": "dashboard"})


@router.get("/presentacion", response_class=HTMLResponse)
def page_presentacion(request: Request):
    """Presentación tipo diapositivas del proyecto (basada en el informe IEEE)."""
    return templates.TemplateResponse(request, "presentacion.html", {"active_nav": "presentacion"})


@router.get("/adquisicion", response_class=HTMLResponse)
def page_acquisition(request: Request):
    """Fase 1 — extracción ChEMBL: embudo, resolución y muestra de datos crudos."""
    return templates.TemplateResponse(request, "analytics_acquisition.html", {"active_nav": "adquisicion"})


@router.get("/api/analytics/glossary")
def glossary():
    """Glosario en español de columnas y métricas."""
    return glossary_payload()


@router.get("/api/analytics/acquisition")
def acquisition():
    """Fase 1: embudo del corpus, resolución PubChem→ChEMBL y muestra de mediciones."""
    funnel = _read_json_any("corpus_funnel.json")
    resolution: dict = {}
    mp = PROJECT_ROOT / "data" / "raw" / "chembl_corpus_mapping.csv"
    if mp.is_file():
        m = pd.read_csv(mp)
        resolution = {
            "by_method": m["match_method"].fillna("not_found").value_counts().astype(int).to_dict(),
            "by_status": m["match_status"].fillna("not_found").value_counts().astype(int).to_dict(),
            "total": int(len(m)),
        }
    act = load_activities()
    sample_cols = [
        c
        for c in (
            "compound_name", "chembl_id", "standard_type", "standard_relation",
            "standard_value", "standard_units", "pchembl_value",
            "target_name", "target_type", "is_censored",
        )
        if c in act.columns
    ]
    sample = act[act["compound_name"].astype(str).str.lower() == "atrazine"][sample_cols].head(8)
    if sample.empty:
        sample = act[sample_cols].head(8)
    return {
        "funnel": funnel,
        "resolution": resolution,
        "sample": {
            "columns": sample_cols,
            "rows": _records(sample),
        },
        "n_measurements": int(len(act)),
        "n_targets": int(act["target_chembl_id"].nunique()) if "target_chembl_id" in act.columns else None,
    }


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


@router.get("/api/analytics/cleaning")
def cleaning():
    """Fase 2: dedup, columnas eliminadas por NaN, censura e imputación (antes/después)."""
    from viz.services.dashboard.cache import load_csv_cached

    raw_path = PROJECT_ROOT / "data" / "raw" / "chembl_panama_bioactivity_raw.csv"
    raw = load_csv_cached(raw_path) if raw_path.is_file() else load_activities()
    act = load_activities()
    THRESH = 250
    dup = 0
    if "potential_duplicate" in raw.columns:
        dup = int(pd.to_numeric(raw["potential_duplicate"], errors="coerce").fillna(0).clip(0, 1).sum())
    nan_counts = raw.isna().sum()
    dropped = [
        {"column": c, "nan": int(n), "pct": round(100 * n / len(raw), 1)}
        for c, n in nan_counts.items() if c not in act.columns
    ]
    dropped.sort(key=lambda x: -x["nan"])
    imputed = 0
    if "pchembl_imputed" in act.columns:
        imputed = int(act["pchembl_imputed"].fillna(False).astype(bool).sum())
    return {
        "raw_rows": int(len(raw)),
        "raw_cols": int(raw.shape[1]),
        "clean_rows": int(len(act)),
        "clean_cols": int(act.shape[1]),
        "dedup_removed": dup,
        "rows_removed_total": int(len(raw) - len(act)),
        "threshold": THRESH,
        "dropped_columns": dropped,
        "censoring": _read_json_any("censoring_report.json"),
        "imputed": imputed,
    }


@router.get("/api/analytics/clusters/sweep")
def clusters_sweep():
    """Barrido de K-means k=2..9: inercia (codo), silueta (rodilla) y etiquetas por k."""
    from sklearn.metrics import adjusted_rand_score
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    from src.analisis_proyecto.core.constants import multivariate_feature_columns

    df = load_chembl()
    cols = [c for c in multivariate_feature_columns() if c in df.columns]
    sub = df.dropna(subset=cols).reset_index(drop=True)
    X = StandardScaler().fit_transform(sub[cols].astype(float).values)
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X)
    ks, inertia, sils, labels = [], [], [], {}
    for k in range(2, 10):
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        ks.append(k); inertia.append(float(km.inertia_))
        sils.append(float(silhouette_score(X, km.labels_)))
        labels[str(k)] = km.labels_.tolist()
    best_k = int(ks[int(np.argmax(sils))])
    best_labels = np.array(labels[str(best_k)])
    ari = float(adjusted_rand_score(sub["family"].astype(str).values, best_labels)) if "family" in sub.columns else None
    pts = [{"pc1": float(coords[i, 0]), "pc2": float(coords[i, 1]),
            "compound_name": str(sub.at[i, "compound_name"]) if "compound_name" in sub else "",
            "family": str(sub.at[i, "family"]) if "family" in sub else ""} for i in range(len(sub))]
    return {
        "ks": ks,
        "inertia": inertia,
        "silhouette": sils,
        "labels": labels,
        "best_k": best_k,
        "points": pts,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "summary": {
            "best_k": best_k,
            "silhouette_best": float(max(sils)) if sils else None,
            "ari_vs_family": ari,
            "pca_var_explained": float(sum(pca.explained_variance_ratio_)),
            "features_used": cols,
            "clustering_space": "7 descriptores estandarizados",
            "projection_space": "PCA 2D solo para visualizacion",
        },
    }


@router.get("/api/analytics/model/compounds")
def model_compounds():
    """Compuestos para el predictor: descriptores + pChEMBL medido; con potencia primero."""
    from src.analisis_proyecto.preprocessing.pipeline import FEATURE_COLS

    allc = load_chembl().copy()
    pot = load_compounds_potency()[["chembl_id", "pchembl_median_binding"]].copy()
    merged = allc.merge(pot, on="chembl_id", how="left")
    keep = ["chembl_id", "compound_name", "family", "pchembl_median_binding"] + [c for c in FEATURE_COLS if c in merged.columns]
    merged = merged[[c for c in keep if c in merged.columns]].copy()
    merged["has_potency"] = merged["pchembl_median_binding"].notna()
    merged["measurement_tag"] = np.where(
        merged["has_potency"],
        "pChEMBL medido",
        "Sin medicion experimental",
    )
    merged = merged.sort_values(
        ["has_potency", "pchembl_median_binding", "compound_name"],
        ascending=[False, False, True],
        na_position="last",
    )
    return {"features": list(FEATURE_COLS), "compounds": _records(merged)}


@router.get("/api/analytics/model/info")
def model_info():
    """Descriptores de entrada (con rangos) + métricas honestas del baseline."""
    from viz.services.dashboard.model import feature_info

    info = feature_info()
    info["metrics"] = load_baseline_honest()
    from viz.glossary import COLUMNS

    info["labels"] = {c: COLUMNS.get(c, {}).get("es", c) for c in info["features"]}
    return info


@router.post("/api/analytics/model/predict")
def model_predict(descriptors: dict):
    """Predice pChEMBL a partir de descriptores (demostrativo — ver métricas)."""
    from viz.services.dashboard.model import predict

    return predict(descriptors or {})


@router.get("/api/analytics/families/stats")
def families_stats():
    """Tests Kruskal y conteos por familia (Fase 4 §3)."""
    return load_family_stats()


@router.get("/api/analytics/dashboard/dataset")
def dashboard_dataset():
    """Datos numéricos a nivel compuesto para el dashboard client-side."""
    df = load_chembl().copy()
    numeric = [c for c in NUMERIC_COLS if c in df.columns]
    # añade descriptores no incluidos en NUMERIC_COLS
    for c in ("num_ro5_violations", "heavy_atoms"):
        if c in df.columns and c not in numeric:
            numeric.append(c)
    keep = ["compound_name", "family"] + numeric
    keep = [c for c in keep if c in df.columns]
    sub = df[keep]
    return {
        "numeric_cols": numeric,
        "families": sorted(df["family"].dropna().unique().tolist()),
        "rows": _records(sub),
    }


@router.get("/api/analytics/compounds-list")
def compounds_list():
    """Lista de compuestos (para el buscador del visor de BD)."""
    df = load_chembl()
    cols = [c for c in ("chembl_id", "compound_name", "family") if c in df.columns]
    return {"compounds": df[cols].fillna("").to_dict(orient="records")}


@router.get("/api/analytics/compound-search")
def compound_search(q: str = Query(..., min_length=1)):
    """Visor de BD real: todas las mediciones (columnas originales) de un compuesto."""
    from viz.services.dashboard.cache import load_csv_cached

    raw_path = PROJECT_ROOT / "data" / "raw" / "chembl_panama_bioactivity_raw.csv"
    df = load_csv_cached(raw_path) if raw_path.is_file() else load_activities()
    ql = q.strip().lower()
    mask = df["compound_name"].astype(str).str.lower().str.contains(ql, na=False, regex=False)
    if "chembl_id" in df.columns:
        mask = mask | df["chembl_id"].astype(str).str.lower().str.contains(ql, na=False, regex=False)
    sub = df[mask]
    total = int(len(sub))
    sub = sub.head(500)
    return {
        "query": q,
        "columns": list(sub.columns),
        "rows": _records(sub),
        "count": total,
        "truncated": total > 500,
    }


@router.post("/api/analytics/refresh")
def refresh_data_cache():
    invalidate_all()
    return {"status": "ok", "message": "Cache invalidado"}
