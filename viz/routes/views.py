"""Rutas HTML (Jinja2) para el dashboard de visualizacion."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from viz.config import TASK_DESCRIPTIONS, TASK_NAMES, TEMPLATES_DIR
from viz.services import corpus

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Dashboard principal: corpus + barra de busqueda."""
    compounds = corpus.list_compounds()
    has_demo = any(c.get("demo") for c in compounds)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "compounds": compounds,
            "has_demo": has_demo,
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
        },
    )


@router.get("/molecule/{compound_id}", response_class=HTMLResponse)
def molecule_detail(request: Request, compound_id: str):
    """Vista detallada de una molecula del corpus."""
    data = corpus.get_compound(compound_id)
    return templates.TemplateResponse(
        request,
        "molecule.html",
        {
            "compound": data,
            "compound_id": compound_id,
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
            "from_corpus": data is not None,
        },
    )


@router.get("/analyze", response_class=HTMLResponse)
def analyze_page(request: Request, smiles: str = ""):
    """Vista de analisis para un SMILES arbitrario."""
    return templates.TemplateResponse(
        request,
        "molecule.html",
        {
            "compound": None,
            "compound_id": None,
            "smiles_input": smiles,
            "task_names": TASK_NAMES,
            "task_descriptions": TASK_DESCRIPTIONS,
            "from_corpus": False,
        },
    )
