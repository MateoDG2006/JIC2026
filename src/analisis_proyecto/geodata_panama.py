"""
Descarga y merge de geodatos de Panamá (Flujo D) para el dashboard Dash.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests

GEOBOUNDARIES_ADM2_API = "https://www.geoboundaries.org/api/current/gbOpen/PAN/ADM2/"
GEOBOUNDARIES_ADM1_API = "https://www.geoboundaries.org/api/current/gbOpen/PAN/ADM1/"

# Densidades aproximadas (hab/km²) por provincia — referencia INEC Censos 2023 (estimación).
PROVINCE_DENSITY: dict[str, float] = {
    "Provincia de Panamá": 280.0,
    "Provincia de Panamá Oeste": 220.0,
    "Provincia de Colón": 95.0,
    "Colón Province": 95.0,
    "Provincia de Chiriquí": 75.0,
    "Provincia de Veraguas": 45.0,
    "Provincia de Los Santos": 55.0,
    "Provincia de Herrera": 60.0,
    "Provincia de Coclé": 65.0,
    "Provincia de Bocas del Toro": 35.0,
    "Provincia de Darién": 12.0,
    "Comarca Ngäbe-Buglé": 25.0,
    "Comarca Guna Yala": 30.0,
    "Comarca Emberá-Wounaan": 18.0,
    "Provincia de Panamá Este": 200.0,
}

# Fracción de superficie agrícola estimada por provincia (MAPI/INEC — valores ilustrativos).
PROVINCE_AG_FRACTION: dict[str, float] = {
    "Provincia de Chiriquí": 0.42,
    "Provincia de Coclé": 0.38,
    "Provincia de Los Santos": 0.45,
    "Provincia de Herrera": 0.40,
    "Provincia de Veraguas": 0.35,
    "Provincia de Darién": 0.15,
    "Provincia de Bocas del Toro": 0.20,
    "Provincia de Colón": 0.12,
    "Colón Province": 0.12,
    "Provincia de Panamá": 0.08,
    "Provincia de Panamá Oeste": 0.15,
    "Provincia de Panamá Este": 0.10,
    "Comarca Ngäbe-Buglé": 0.25,
    "Comarca Guna Yala": 0.10,
    "Comarca Emberá-Wounaan": 0.12,
}

# Índice de pobreza multidimensional aproximado (0–100, mayor = más pobreza).
PROVINCE_POVERTY_INDEX: dict[str, float] = {
    "Provincia de Darién": 38.0,
    "Comarca Ngäbe-Buglé": 45.0,
    "Comarca Emberá-Wounaan": 42.0,
    "Provincia de Bocas del Toro": 32.0,
    "Provincia de Colón": 28.0,
    "Colón Province": 28.0,
    "Provincia de Veraguas": 24.0,
    "Provincia de Herrera": 22.0,
    "Provincia de Los Santos": 20.0,
    "Provincia de Coclé": 18.0,
    "Provincia de Chiriquí": 16.0,
    "Provincia de Panamá": 12.0,
    "Provincia de Panamá Oeste": 14.0,
    "Provincia de Panamá Este": 13.0,
    "Comarca Guna Yala": 35.0,
}


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_geojson_url(api_url: str) -> str:
    resp = requests.get(api_url, timeout=60)
    resp.raise_for_status()
    meta = resp.json()
    url = meta.get("simplifiedGeometryGeoJSON") or meta.get("gjDownloadURL")
    if not url:
        raise RuntimeError(f"No se encontró URL GeoJSON en {api_url}")
    return url


def download_district_boundaries(output_path: str | Path) -> gpd.GeoDataFrame:
    """Descarga distritos (ADM2) de Panamá desde geoBoundaries."""
    url = _fetch_geojson_url(GEOBOUNDARIES_ADM2_API)
    gdf = gpd.read_file(url)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    return gdf


def _assign_provinces(districts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Asigna provincia a cada distrito vía join espacial ADM1."""
    prov_url = _fetch_geojson_url(GEOBOUNDARIES_ADM1_API)
    provinces = gpd.read_file(prov_url)
    districts = districts.copy()
    districts = districts.to_crs(provinces.crs)
    projected = districts.to_crs(epsg=32617)
    centroids = projected.copy()
    centroids["geometry"] = centroids.geometry.centroid
    centroids = centroids.to_crs(provinces.crs)
    joined = gpd.sjoin(
        centroids,
        provinces[["shapeName", "geometry"]].rename(columns={"shapeName": "provincia"}),
        how="left",
        predicate="within",
    )
    province_map = dict(zip(joined.index, joined["provincia"], strict=False))
    districts["provincia"] = districts.index.map(province_map)
    missing = districts["provincia"].isna().sum()
    if missing:
        districts.loc[districts["provincia"].isna(), "provincia"] = "Sin asignar"
    return districts


def _deterministic_jitter(name: str, low: float = 0.85, high: float = 1.15) -> float:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    frac = int(digest[:8], 16) / 0xFFFFFFFF
    return low + (high - low) * frac


def build_inec_sociodemographic_table(districts: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Construye tabla sociodemográfica a nivel distrito.

    Estrategia: estimaciones reproducibles a partir de área y provincia,
    alineadas con estructura INEC MAPI. Sustituir por descarga MAPI cuando esté disponible.
    """
    gdf = districts.to_crs(epsg=32617)  # UTM zona 17N — Panamá
    rows: list[dict[str, Any]] = []

    for idx, row in gdf.iterrows():
        distrito = str(row.get("shapeName", row.get("distrito", f"distrito_{idx}")))
        provincia = str(row.get("provincia", "Sin asignar"))
        area_km2 = max(float(row.geometry.area) / 1_000_000.0, 0.1)
        density = PROVINCE_DENSITY.get(provincia, 40.0) * _deterministic_jitter(distrito)
        poblacion = int(area_km2 * density)
        ag_frac = PROVINCE_AG_FRACTION.get(provincia, 0.20) * _deterministic_jitter(
            distrito + "_ag", 0.9, 1.1
        )
        superficie_agricola_ha = round(area_km2 * 100 * ag_frac, 1)
        poverty_base = PROVINCE_POVERTY_INDEX.get(provincia, 25.0)
        indice_pobreza = round(
            poverty_base * _deterministic_jitter(distrito + "_pov", 0.92, 1.08), 1
        )

        rows.append(
            {
                "codigo_distrito": f"PAN-{idx:03d}",
                "nombre_distrito": distrito,
                "nombre_norm": _normalize_name(distrito),
                "provincia": provincia,
                "area_km2": round(area_km2, 2),
                "poblacion": poblacion,
                "superficie_agricola_ha": superficie_agricola_ha,
                "indice_pobreza": indice_pobreza,
                "fuente": "estimacion_geografica_inec_mapi",
            }
        )

    return pd.DataFrame(rows)


def merge_districts_with_inec(
    districts: gpd.GeoDataFrame,
    inec_df: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Une límites administrativos con variables sociodemográficas."""
    gdf = districts.copy()
    gdf["nombre_distrito"] = gdf["shapeName"]
    gdf["nombre_norm"] = gdf["nombre_distrito"].map(_normalize_name)

    inec = inec_df.copy()
    if "nombre_norm" not in inec.columns:
        inec["nombre_norm"] = inec["nombre_distrito"].map(_normalize_name)

    inec_merge = inec.drop(columns=["nombre_distrito", "provincia"], errors="ignore")
    merged = gdf.merge(inec_merge, on="nombre_norm", how="left")
    if "provincia_x" in merged.columns:
        merged["provincia"] = merged["provincia_x"].fillna(merged.get("provincia_y"))
        merged = merged.drop(columns=["provincia_x", "provincia_y"], errors="ignore")
    return merged


def build_panama_geodata(
    raw_geojson: str | Path,
    inec_csv: str | Path,
    merged_geojson: str | Path,
) -> dict[str, Any]:
    """
    Pipeline completo: descarga distritos, genera INEC, merge y exporta GeoJSON.
    """
    raw_geojson = Path(raw_geojson)
    inec_csv = Path(inec_csv)
    merged_geojson = Path(merged_geojson)

    districts = download_district_boundaries(raw_geojson)
    districts = _assign_provinces(districts)
    inec_df = build_inec_sociodemographic_table(districts)
    inec_csv.parent.mkdir(parents=True, exist_ok=True)
    inec_df.to_csv(inec_csv, index=False)

    merged = merge_districts_with_inec(districts, inec_df)
    merged_geojson.parent.mkdir(parents=True, exist_ok=True)
    merged.to_file(merged_geojson, driver="GeoJSON")

    unmatched = merged["poblacion"].isna().sum() if "poblacion" in merged.columns else 0
    prov_col = merged["provincia"] if "provincia" in merged.columns else pd.Series(dtype=str)
    report = {
        "n_distritos": len(merged),
        "n_provincias": int(prov_col.nunique()) if len(prov_col) else 0,
        "distritos_sin_match_inec": int(unmatched),
        "raw_geojson": str(raw_geojson),
        "inec_csv": str(inec_csv),
        "merged_geojson": str(merged_geojson),
    }
    return report
