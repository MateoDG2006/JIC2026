"""Rutas HTML (Jinja2) para el visor GNN 3D.

Estas rutas sirven las páginas del visor — la lógica interactiva
(predicción, XAI, render 3D con 3Dmol.js) la hace el JavaScript
del cliente, que pega a los endpoints de ``viz.routes.api``.

Endpoints:
    GET /                       → corpus Panamá por familia
    GET /molecule/{compound_id} → predicción en vivo de compuesto del catálogo
    GET /analyze?smiles=...     → análisis ad-hoc (SMILES / PubChem)
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from viz.config import TASK_DESCRIPTIONS, TASK_NAMES, TEMPLATES_DIR
from viz.services import panama_corpus

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Dashboard principal: corpus Panamá por familia + buscador."""
    families = panama_corpus.list_by_family()
    total = sum(section["count"] for section in families)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "active_nav": "viewer",
            "families": families,
            "total_compounds": total,
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
        },
    )


@router.get("/molecule/{compound_id}", response_class=HTMLResponse)
def molecule_detail(request: Request, compound_id: str):
    """Redirige al análisis en vivo de un compuesto del corpus Panamá."""
    data = panama_corpus.get_compound(compound_id)
    if data is None:
        return templates.TemplateResponse(
            request,
            "molecule.html",
            {
                "compound": None,
                "compound_id": compound_id,
                "active_nav": "viewer",
                "task_names": TASK_NAMES,
                "task_descriptions": TASK_DESCRIPTIONS,
                "from_corpus": False,
                "smiles_input": "",
                "compound_name": "",
                "compound_family": "",
                "live_analysis": False,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "molecule.html",
        {
            "compound": None,
            "compound_id": compound_id,
            "active_nav": "viewer",
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
            "from_corpus": True,
            "smiles_input": data["smiles"],
            "compound_name": data["name"],
            "compound_family": data["family"],
            "live_analysis": True,
        },
    )


@router.get("/analyze", response_class=HTMLResponse)
def analyze_page(
    request: Request,
    smiles: str = "",
    name: str = "",
    family: str = "",
):
    """Vista de analisis para un SMILES arbitrario (inferencia en vivo)."""
    return templates.TemplateResponse(
        request,
        "molecule.html",
        {
            "compound": None,
            "compound_id": None,
            "smiles_input": smiles,
            "compound_name": name,
            "compound_family": family,
            "active_nav": "viewer",
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
            "from_corpus": False,
            "live_analysis": bool(smiles),
        },
    )
