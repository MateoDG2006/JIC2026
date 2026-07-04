"""Endpoints REST para predicción GIN, XAI y utilidades moleculares.

Cliente esperado: el JavaScript del visor (``viz/static/js/molecule.js``)
y cualquier integración externa. Todos los endpoints aceptan/devuelven JSON
y arrojan ``HTTPException`` 4xx/5xx con mensaje legible si algo falla.

Endpoints (montados bajo ``/api``):

    GET  /status              → estado del modelo y corpus
    GET  /corpus              → lista de compuestos precomputados
    GET  /corpus/{id}         → detalles de un compuesto del corpus
    POST /corpus/reload       → recarga corpus desde disco

    POST /predict   {smiles}                           → 12 probabilidades Tox21
    POST /explain   {smiles, task, method}             → importancia por átomo + colores
    POST /analyze   {smiles}                           → predict + XAI + propiedades
    POST /svg       {smiles, importance, title}        → SVG 2D coloreado
    POST /xai-colors {importance}                      → colores hex YlOrRd

    GET  /mol3d?smiles=...    → SDF / MOL block para 3Dmol.js
    GET  /stl?smiles=...&style=...  → STL 3D (ballstick) o plano (flat_keychain)
    GET  /properties?smiles=  → MW, LogP, PSA, etc. (RDKit Descriptors)
    GET  /pubchem/search?q=   → búsqueda por nombre en PubChem (CID + imagen)
    GET  /tasks               → lista de 12 tareas Tox21 con descripción
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from viz.config import TASK_NAMES
from viz.services import corpus
from viz.services.molecule import (
    atom_symbols,
    molecular_properties,
    smiles_to_mol_block,
    smiles_to_sdf,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
def api_status():
    """Estado del servidor: modelo, corpus y dispositivo."""
    from viz.services import inference

    return {
        "model_available": inference.model_available(),
        "model_loaded": inference._model is not None,
        "model_error": inference.get_model_error(),
        "corpus_count": len(corpus.list_compounds()),
        "device": str(inference.get_device()),
        "cuda": inference.get_device().type == "cuda",
    }


class PredictRequest(BaseModel):
    smiles: str


class ExplainRequest(BaseModel):
    smiles: str
    task: str
    method: str = "gradcam"


# --- Corpus pre-computado ---


@router.get("/corpus")
def list_corpus():
    """Lista todos los compuestos pre-computados."""
    return corpus.list_compounds()


@router.get("/corpus/{compound_id}")
def get_corpus_compound(compound_id: str):
    """Datos completos de un compuesto del corpus."""
    data = corpus.get_compound(compound_id)
    if data is None:
        raise HTTPException(404, f"Compuesto '{compound_id}' no encontrado")
    return data


@router.get("/corpus/reload")
def reload_corpus():
    """Recarga el corpus pre-computado legacy desde disco."""
    n = corpus.reload_corpus()
    return {"reloaded": n}


@router.get("/panama/compounds")
def list_panama_compounds():
    """Lista plana del catálogo panameño (sin predicciones)."""
    from viz.services import panama_corpus

    return panama_corpus.list_compounds()


@router.get("/panama/families")
def list_panama_families():
    """Catálogo panameño agrupado por familia química."""
    from viz.services import panama_corpus

    return panama_corpus.list_by_family()


@router.get("/panama/compounds/{compound_id}")
def get_panama_compound(compound_id: str):
    """Metadatos de un compuesto del catálogo panameño."""
    from viz.services import panama_corpus

    data = panama_corpus.get_compound(compound_id)
    if data is None:
        raise HTTPException(404, f"Compuesto '{compound_id}' no encontrado")
    return data


@router.post("/panama/reload")
def reload_panama_catalog():
    """Recarga el catálogo panameño desde CSV."""
    from viz.services import panama_corpus

    n = panama_corpus.reload_catalog()
    return {"reloaded": n}


# --- Inferencia en vivo ---


@router.post("/predict")
def predict_smiles(req: PredictRequest):
    """Ejecuta prediccion del modelo GIN sobre un SMILES arbitrario."""
    from viz.services.inference import model_available, predict

    if not model_available():
        raise HTTPException(
            503,
            "Modelo no disponible. Ejecuta: make train-gin",
        )

    try:
        result = predict(req.smiles)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    if result is None:
        raise HTTPException(400, f"SMILES invalido: {req.smiles}")
    return {"smiles": req.smiles, "predictions": result}


@router.post("/explain")
def explain_smiles(req: ExplainRequest):
    """Genera explicacion XAI para un SMILES y una tarea especifica."""
    if req.task not in TASK_NAMES:
        raise HTTPException(400, f"Tarea invalida: {req.task}")

    from viz.services.inference import (
        explain_gnnexplainer,
        explain_gradcam,
        model_available,
    )

    if not model_available():
        raise HTTPException(503, "Modelo no disponible. Ejecuta: make train-gin")

    task_idx = TASK_NAMES.index(req.task)

    try:
        if req.method == "gnnexplainer":
            importance = explain_gnnexplainer(req.smiles, task_idx)
        elif req.method == "gradcam":
            importance = explain_gradcam(req.smiles, task_idx)
        else:
            raise HTTPException(400, f"Metodo invalido: {req.method}")
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    if importance is None:
        raise HTTPException(500, "Error generando explicacion XAI")

    import numpy as np
    from src.xai.visualizer import importance_to_hex_colors

    return {
        "smiles": req.smiles,
        "task": req.task,
        "method": req.method,
        "importance": importance,
        "atom_colors": importance_to_hex_colors(np.array(importance)),
        "atom_symbols": atom_symbols(req.smiles),
    }


@router.post("/analyze")
def full_analysis(req: PredictRequest):
    """Prediccion completa + XAI para todas las tareas relevantes."""
    from viz.services.inference import full_analysis as _analyze, model_available

    if not model_available():
        raise HTTPException(503, "Modelo no disponible. Ejecuta: make train-gin")

    try:
        result = _analyze(req.smiles)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    if result is None:
        raise HTTPException(400, f"SMILES invalido: {req.smiles}")

    mol_block = smiles_to_mol_block(req.smiles)
    result["mol_block"] = mol_block
    return result


class SvgRequest(BaseModel):
    smiles: str
    importance: list[float]
    title: str = ""


@router.post("/svg")
def render_svg(req: SvgRequest):
    """Genera SVG 2D de la molecula coloreada por importancia XAI."""
    import numpy as np
    from src.xai.visualizer import (
        draw_molecule_with_importance,
        importance_to_hex_colors,
    )

    try:
        imp = np.array(req.importance)
        svg = draw_molecule_with_importance(req.smiles, imp, title=req.title)
        colors = importance_to_hex_colors(imp)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"svg": svg, "atom_colors": colors}


class ColorsRequest(BaseModel):
    importance: list[float]


@router.post("/xai-colors")
def xai_colors(req: ColorsRequest):
    """Colores hex YlOrRd (idénticos al SVG) para un vector de importancias."""
    import numpy as np
    from src.xai.visualizer import importance_to_hex_colors

    if not req.importance:
        raise HTTPException(400, "importance vacío")
    return {"atom_colors": importance_to_hex_colors(np.array(req.importance))}


# --- Utilidades moleculares ---


@router.get("/mol3d")
def get_mol3d(smiles: str):
    """Genera estructura 3D (SDF + MOL block) para un SMILES."""
    sdf = smiles_to_sdf(smiles)
    block = smiles_to_mol_block(smiles)
    if sdf is None and block is None:
        raise HTTPException(400, f"No se pudo generar 3D para: {smiles}")
    return {
        "smiles": smiles,
        "sdf": sdf,
        "mol_block": block,
        "format": "sdf" if sdf else "mol",
    }


@router.get("/stl")
def get_stl(
    smiles: str,
    name: str = "molecule",
    style: str = "ballstick",
    mol_height: float | None = None,
    ring_side: str | None = None,
):
    """Genera malla STL para impresión 3D (ball-and-stick o plano para llavero)."""
    from viz.services.stl_export import smiles_to_stl, smiles_to_stl_flat_keychain

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:64] or "molecule"
    style_key = style.strip().lower()

    if style_key in ("flat", "flat_keychain", "keychain", "llavero"):
        stl = smiles_to_stl_flat_keychain(
            smiles,
            title=safe_name,
            label=name,
            mol_height_above_plate=mol_height,
            keyring_side=ring_side,
        )
        suffix = "_llavero"
    else:
        stl = smiles_to_stl(smiles, title=safe_name)
        suffix = ""

    if stl is None:
        raise HTTPException(400, f"No se pudo generar STL para: {smiles}")
    return Response(
        content=stl,
        media_type="model/stl",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}{suffix}.stl"'},
    )


@router.get("/pubchem/search")
def pubchem_search(q: str, limit: int = 10):
    """Busca compuestos en PubChem por nombre (autocomplete + propiedades)."""
    import requests

    from viz.services.pubchem import search_compounds

    query = q.strip()
    if not query:
        raise HTTPException(400, "Ingresa al menos un carácter para buscar")

    try:
        results = search_compounds(query, limit=limit)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Error consultando PubChem: {exc}") from exc

    return {"query": query, "count": len(results), "results": results}


@router.get("/properties")
def get_properties(smiles: str):
    """Propiedades fisicoquimicas de un SMILES."""
    props = molecular_properties(smiles)
    if props is None:
        raise HTTPException(400, f"SMILES invalido: {smiles}")
    return props


@router.get("/tasks")
def get_tasks():
    """Lista de tareas Tox21 con descripciones."""
    from viz.config import TASK_DESCRIPTIONS
    return [
        {"name": t, "description": TASK_DESCRIPTIONS.get(t, "")}
        for t in TASK_NAMES
    ]
