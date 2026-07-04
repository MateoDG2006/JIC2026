"""Servicio HTTP read-only sobre ChEMBLdb SQLite (contenedor Docker)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.analisis_proyecto.acquisition.local import ChemblDatabase


def server_db_path() -> str:
    return os.environ.get("CHEMBL_DB_PATH", "/data/chembl/chembl_37.db")


_db: ChemblDatabase | None = None


def get_db() -> ChemblDatabase:
    global _db
    if _db is None:
        _db = ChemblDatabase(server_db_path())
    return _db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_db()
    yield


app = FastAPI(title="ChEMBL SQLite Server", version="1.0", lifespan=lifespan)


class ActivitiesRequest(BaseModel):
    chembl_ids: list[str]
    standard_types: list[str] = Field(default_factory=list)


class MappingRequest(BaseModel):
    compounds: list[dict[str, Any]]
    existing: dict[str, dict[str, Any]] = Field(default_factory=dict)
    skip_resolved: bool = True
    verbose: bool = False


class BioactivityRequest(BaseModel):
    mapping: list[dict[str, Any]]
    standard_types: list[str] = Field(default_factory=list)
    pchembl_threshold: float = 6.0
    verbose: bool = False


@app.get("/health")
def health() -> dict[str, bool]:
    get_db()
    return {"ok": True}


@app.get("/info")
def info() -> dict[str, Any]:
    return get_db().info().to_dict()


@app.post("/fetch_activities")
def fetch_activities(body: ActivitiesRequest) -> dict[str, list[dict[str, Any]]]:
    types = tuple(body.standard_types) if body.standard_types else None
    df = get_db().fetch_activities(body.chembl_ids, standard_types=types)
    return {"records": df.to_dict(orient="records")}


@app.post("/build_mapping")
def build_mapping(body: MappingRequest) -> dict[str, list[dict[str, Any]]]:
    compounds_df = pd.DataFrame(body.compounds)
    df = get_db().build_mapping_table(
        compounds_df,
        verbose=body.verbose,
        existing_resolved=body.existing or None,
        skip_resolved=body.skip_resolved,
    )
    return {"records": df.to_dict(orient="records")}


@app.post("/build_bioactivity")
def build_bioactivity(body: BioactivityRequest) -> dict[str, list[dict[str, Any]]]:
    mapping_df = pd.DataFrame(body.mapping)
    types = tuple(body.standard_types) if body.standard_types else None
    df = get_db().build_bioactivity_table(
        mapping_df,
        verbose=body.verbose,
        standard_types=types,
        pchembl_threshold=body.pchembl_threshold,
    )
    return {"records": df.to_dict(orient="records")}


def main() -> None:
    import uvicorn

    host = os.environ.get("CHEMBL_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("CHEMBL_SERVER_PORT", "8765"))
    uvicorn.run("src.analisis_proyecto.acquisition.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
