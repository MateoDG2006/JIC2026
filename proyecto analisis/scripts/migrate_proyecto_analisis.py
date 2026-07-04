#!/usr/bin/env python
"""Migra el proyecto de análisis ChEMBL a ``proyecto analisis/`` (monorepo JIC2026)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

MONOREPO = Path(__file__).resolve().parents[1]
PA = MONOREPO / "proyecto analisis"

RAW_CHEMBL = [
    "chembl_panama_bioactivity.csv",
    "chembl_panama_bioactivity_raw.csv",
    "chembl_corpus_compounds.csv",
    "chembl_corpus_mapping.csv",
    "chembl_mida_compounds.csv",
    "chembl_mida_mapping.csv",
    "panama_distritos.geojson",
    "inec_sociodemografico.csv",
    "pubchem_panama_cids.csv",
]

PROCESSED_CHEMBL = [
    "activities_clean.csv",
    "compounds_features.csv",
    "chembl_clean.csv",
    "panama_distritos_merged.geojson",
    "geodata_manifest.json",
]

DASHBOARD_CHEMBL_JSON = [
    "correlation_pearson.json",
    "model_eval.json",
    "model_comparison.json",
    "pchembl_imputation.json",
    "predictor_defaults.json",
    "manifest.json",
]


def mkdirs() -> None:
    for rel in (
        "config",
        "data/raw",
        "data/processed",
        "data/external/chembl",
        "src/analisis_proyecto",
        "src/data",
        "notebooks",
        "docs/fases",
        "outputs/chembl/figures",
        "outputs/chembl/models",
        "outputs/chembl/results",
        "outputs/dashboard",
        "scripts/fase1",
        "scripts/fase4",
        "scripts/fase5",
        "scripts/fase6",
        "docker/chembl-init",
        "viz/routes",
        "viz/services/dashboard",
        "viz/templates",
        "viz/static/js",
        "mateo_docs/planes",
    ):
        (PA / rel).mkdir(parents=True, exist_ok=True)


def move_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if src.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))
    print(f"  moved {src.relative_to(MONOREPO)} -> {dst.relative_to(MONOREPO)}")


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"  copied {src.relative_to(MONOREPO)} -> {dst.relative_to(MONOREPO)}")


def move_trees() -> None:
    print("=== Moving directories ===")
    moves = [
        (MONOREPO / "docs" / "analisis_proyecto", PA / "docs"),
        (MONOREPO / "outputs" / "chembl", PA / "outputs" / "chembl"),
        (MONOREPO / "docker" / "chembl-init", PA / "docker" / "chembl-init"),
        (MONOREPO / "data" / "external" / "chembl", PA / "data" / "external" / "chembl"),
    ]
    nb_src = MONOREPO / "notebooks" / "proyecto analisis de datos"
    nb_dst = PA / "notebooks"
    if nb_src.exists() and any(nb_src.iterdir()) and not any(nb_dst.glob("*.ipynb")):
        moves.insert(0, (nb_src, nb_dst))
    elif nb_src.exists() and not any(nb_src.iterdir()):
        try:
            nb_src.rmdir()
        except OSError:
            pass
    for src, dst in moves:
        move_if_exists(src, dst)

    scripts_src = MONOREPO / "scripts" / "analisis_proyecto"
    if scripts_src.exists():
        for item in scripts_src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(scripts_src)
                move_if_exists(item, PA / "scripts" / rel)
        # cleanup empty dirs
        for d in sorted(scripts_src.rglob("*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except OSError:
                    pass
        try:
            scripts_src.rmdir()
        except OSError:
            pass

    for name in RAW_CHEMBL:
        move_if_exists(MONOREPO / "data" / "raw" / name, PA / "data" / "raw" / name)

    for name in PROCESSED_CHEMBL:
        move_if_exists(MONOREPO / "data" / "processed" / name, PA / "data" / "processed" / name)

    for name in DASHBOARD_CHEMBL_JSON:
        move_if_exists(MONOREPO / "outputs" / "dashboard" / name, PA / "outputs" / "dashboard" / name)

    # Analytics viz slice
    viz_moves = [
        (MONOREPO / "viz" / "routes" / "analytics.py", PA / "viz" / "routes" / "analytics.py"),
        (MONOREPO / "viz" / "services" / "dashboard", PA / "viz" / "services" / "dashboard"),
    ]
    for src, dst in viz_moves:
        move_if_exists(src, dst)

    for pattern in ("analytics_*.html",):
        for f in (MONOREPO / "viz" / "templates").glob(pattern):
            move_if_exists(f, PA / "viz" / "templates" / f.name)

    for pattern in ("analytics_*.js",):
        for f in (MONOREPO / "viz" / "static" / "js").glob(pattern):
            move_if_exists(f, PA / "viz" / "static" / "js" / f.name)

    move_if_exists(
        MONOREPO / "scripts" / "fase5" / "prepare_dashboard.py",
        PA / "scripts" / "fase5" / "prepare_dashboard.py",
    )

    pasamano = MONOREPO / "mateo_docs" / "planes" / "PASAMANO_CURSOR_opcion_A.md"
    if pasamano.exists():
        copy_if_exists(pasamano, PA / "mateo_docs" / "planes" / pasamano.name)


def write_paths_module() -> None:
    content = '''"""Rutas del proyecto de análisis (ChEMBL)."""
from __future__ import annotations

import sys
from pathlib import Path

# Raíz de ``proyecto analisis/`` (padre de ``src/``)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = PROJECT_ROOT.parent


def setup_path() -> Path:
    """Añade PROJECT_ROOT a sys.path para imports ``from src....``."""
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return PROJECT_ROOT
'''
    (PA / "src" / "paths.py").write_text(content, encoding="utf-8")
    (PA / "src" / "__init__.py").write_text('"""Proyecto análisis de datos — ChEMBL Panamá."""\n', encoding="utf-8")


def write_mida_module() -> None:
    content = '''"""Ingredientes activos MIDA (Panamá) — lista usada en extracción ChEMBL."""

MIDA_ACTIVE_INGREDIENTS: list[str] = [
    "Chlorpyrifos", "Malathion", "Dimethoate", "Methyl parathion",
    "Carbaryl", "Methomyl", "Aldicarb",
    "Atrazine", "Simazine",
    "Tebuconazole", "Propiconazole", "Difenoconazole",
    "Cypermethrin", "Deltamethrin", "Lambda-cyhalothrin",
    "Glyphosate", "Paraquat", "2,4-D", "Mancozeb", "Chlorothalonil",
]
'''
    (PA / "src" / "data" / "__init__.py").write_text("", encoding="utf-8")
    (PA / "src" / "data" / "mida.py").write_text(content, encoding="utf-8")


def write_config() -> None:
    content = '''# Configuración — Proyecto Análisis de Datos (ChEMBL Panamá)

chembl:
  backend: sqlite
  version: "37"
  db_path: data/external/chembl/chembl_37.db
  ftp_url: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_37_sqlite.tar.gz
  pchembl_active_threshold: 6.0
  corpus_mode: full
  standard_types:
    - IC50
    - EC50
    - Ki
    - Kd
    - Potency
    - Inhibition
    - AC50
    - LC50
    - GI50
    - MIC
    - LD50
    - ED50
    - IC90
  quality_filters:
    impute_pchembl: true
    require_exact_relation: true
    exclude_validity_comment: true

viz:
  host: 127.0.0.1
  port: 8001
  artifacts_dir: outputs/dashboard
  bundle_dir: outputs/dashboard/bundle
'''
    (PA / "config" / "config.yaml").write_text(content, encoding="utf-8")


def write_viz_app() -> None:
    (PA / "viz" / "__init__.py").write_text('"""Visor analytics ChEMBL (FastAPI)."\n', encoding="utf-8")
    (PA / "viz" / "routes" / "__init__.py").write_text("", encoding="utf-8")
    (PA / "viz" / "services" / "__init__.py").write_text("", encoding="utf-8")

    config_py = '''"""Configuración del visor analytics ChEMBL."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

from src.paths import MONOREPO_ROOT, PROJECT_ROOT, setup_path

setup_path()

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "dashboard"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
CHEMBL_CSV = DATA_DIR / "compounds_features.csv"
CHEMBL_CSV_LEGACY = DATA_DIR / "chembl_clean.csv"
ACTIVITIES_CSV = DATA_DIR / "activities_clean.csv"
CHEMBL_MODELS_DIR = PROJECT_ROOT / "outputs" / "chembl" / "models"
CHEMBL_METRICS = PROJECT_ROOT / "outputs" / "chembl" / "results" / "stats_tests.csv"
GEOJSON_PATH = DATA_DIR / "panama_distritos_merged.geojson"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Perfil GNN (proyecto hermano JIC) — solo comparativa / mapa tóxico
TOXICITY_PROFILE_CSV = MONOREPO_ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv"
PANAMA_CIDS_CSV = PROJECT_ROOT / "data" / "raw" / "pubchem_panama_cids.csv"
XAI_FIGURES_DIR = MONOREPO_ROOT / "outputs" / "xai" / "figures"

NUMERIC_COLS = [
    "pchembl_median", "pchembl_value", "mw_freebase", "alogp", "psa", "hba", "hbd",
    "aromatic_rings", "rtb", "num_ro5_violations", "standard_value",
]

FEATURE_LABELS: dict[str, str] = {
    "mw_freebase": "Peso molecular (MW)",
    "alogp": "LogP",
    "psa": "PSA",
    "hba": "HBA",
    "hbd": "HBD",
    "aromatic_rings": "Anillos aromáticos",
    "rtb": "Enlaces rotables",
    "num_ro5_violations": "Violaciones Lipinski",
}

PREDICTOR_NOTE = (
    "Proyecto descriptivo (Opción A): sin predictor pChEMBL. "
    "Ver anexo_baseline_predictivo.ipynb para el baseline honesto."
)


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def use_bundle() -> bool:
    env = os.environ.get("DASHBOARD_BUNDLE", "").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return not CHEMBL_CSV.is_file() and (BUNDLE_DIR / "compounds_features.csv").is_file()


def resolve_path(canonical: Path, bundle_name: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_name
        if bundle_path.is_file():
            return bundle_path
    return canonical


def resolve_dir(canonical: Path, bundle_subdir: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_subdir
        if bundle_path.is_dir():
            return bundle_path
    return canonical


def viz_host() -> str:
    return os.environ.get("VIZ_ANALYTICS_HOST") or _load_yaml().get("viz", {}).get("host", "127.0.0.1")


def viz_port() -> int:
    return int(os.environ.get("VIZ_ANALYTICS_PORT") or _load_yaml().get("viz", {}).get("port", 8001))
'''
    (PA / "viz" / "config.py").write_text(config_py, encoding="utf-8")

    app_py = '''"""Visor FastAPI — Proyecto Análisis de Datos (ChEMBL / Panamá)."""
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
'''
    (PA / "viz" / "app.py").write_text(app_py, encoding="utf-8")


def write_requirements() -> None:
    content = '''# Proyecto Análisis de Datos — ChEMBL Panamá
# Python >=3.10,<3.13

numpy>=1.24
pandas>=2.0
scipy>=1.11
scikit-learn>=1.3
scikit-posthocs>=0.9.0
matplotlib>=3.7
seaborn>=0.13
PyYAML>=6.0
requests>=2.31
chembl-webresource-client>=0.10.8
missingno>=0.5.2
upsetplot>=0.9.0
geopandas>=0.14
folium>=0.15
jupyter>=1.0
fastapi>=0.110
uvicorn>=0.27
joblib>=1.3
pytest>=7.4
'''
    (PA / "requirements.txt").write_text(content, encoding="utf-8")


def write_readme() -> None:
    content = '''# Proyecto Análisis de Datos — ChEMBL × Plaguicidas Panamá

Curso de análisis de datos sobre bioactividad ChEMBL de ingredientes activos del MIDA.
**Separado del proyecto GNN (JIC 2026)** en el monorepo `JIC2026/`.

## Estructura

```
proyecto analisis/
├── config/config.yaml       # ChEMBL + viz analytics
├── data/
│   ├── raw/                 # Extracción ChEMBL + geodatos
│   ├── processed/           # activities_clean + compounds_features (107)
│   └── external/chembl/     # chembl_37.db (SQLite local)
├── src/analisis_proyecto/   # Pipeline Python
├── notebooks/               # Fases 1–7 + anexo baseline
├── docs/                    # Documentación por fase
├── outputs/chembl/          # Figuras, modelos legacy, resultados
├── outputs/dashboard/       # JSON para viz analytics
├── scripts/                 # CLI por fase
├── docker/chembl-init/      # Descarga BD ChEMBL
└── viz/                     # FastAPI analytics (puerto 8001)
```

## Inicio rápido

```bash
cd "proyecto analisis"
pip install -r requirements.txt

# Verificación pipeline Opción A
python scripts/fase4/verify_flow_b.py

# Notebooks (orden)
jupyter notebook notebooks/fase2_limpieza.ipynb

# Visor analytics
python viz/app.py
```

## Unidad de análisis

**107 compuestos** (`compounds_features.csv`), no filas de medición.
El baseline predictivo está en `notebooks/anexo_baseline_predictivo.ipynb`.

## Proyecto hermano

El GNN-GIN + XAI vive en la raíz del monorepo (`src/models/gin.py`, `notebooks/04_gnn_training.ipynb`).
'''
    (PA / "README.md").write_text(content, encoding="utf-8")


def patch_file(path: Path, replacements: list[tuple[str, str]]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print(f"  patched {path.relative_to(MONOREPO)}")


def patch_python_files() -> None:
    print("=== Patching Python files ===")
    replacements_common = [
        ("from src.data.pubchem_api import MIDA_ACTIVE_INGREDIENTS", "from src.data.mida import MIDA_ACTIVE_INGREDIENTS"),
        ("Path(__file__).resolve().parents[3]", "Path(__file__).resolve().parents[2]"),
        ('parents[2] / "fase5" / "prepare_dashboard.py"', 'Path(__file__).resolve().parent / "prepare_dashboard.py"'),
        ('parents[2] / "fase5" / "test_dashboard.py"', 'Path(__file__).resolve().parent / "test_dashboard.py"'),
    ]

    for py in PA.rglob("*.py"):
        reps = list(replacements_common)
        if py.name == "chembl_extract.py":
            reps.append(
                (
                    "def _project_root() -> Path:\n    return Path(__file__).resolve().parents[2]",
                    "def _project_root() -> Path:\n    from src.paths import PROJECT_ROOT\n    return PROJECT_ROOT",
                )
            )
        if py.name in ("run_opcion_a_outputs.py", "write_opcion_a_notebooks.py"):
            reps.append(
                (
                    "ROOT = Path(__file__).resolve().parents[2]",
                    "ROOT = Path(__file__).resolve().parents[1]",
                )
            )
        if py.name == "verify_flow_b.py":
            reps.append(
                (
                    "ROOT = Path(__file__).resolve().parents[3]",
                    "ROOT = Path(__file__).resolve().parents[2]",
                )
            )
        patch_file(py, reps)

    # chembl_api import
    patch_file(PA / "src" / "analisis_proyecto" / "chembl_api.py", replacements_common)

    # prepare_dashboard
    patch_file(
        PA / "scripts" / "fase5" / "prepare_dashboard.py",
        [
            ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parents[2]  # proyecto analisis root"),
            ("from src.data.pubchem_api import MIDA_ACTIVE_INGREDIENTS", "from src.data.mida import MIDA_ACTIVE_INGREDIENTS"),
            ('CHEMBL_CSV = ROOT / "data" / "processed" / "chembl_clean.csv"', 'CHEMBL_CSV = ROOT / "data" / "processed" / "compounds_features.csv"'),
        ],
    )

    # JIC viz config — point chembl paths to proyecto analisis
    jic_viz_config = MONOREPO / "viz" / "config.py"
    if jic_viz_config.is_file():
        text = jic_viz_config.read_text(encoding="utf-8")
        if "ANALISIS_ROOT" not in text:
            insert = '''
ANALISIS_ROOT = PROJECT_ROOT / "proyecto analisis"
'''
            text = text.replace(
                "PROJECT_ROOT = Path(__file__).resolve().parents[1]",
                "PROJECT_ROOT = Path(__file__).resolve().parents[1]\n" + insert.strip(),
            )
            text = text.replace(
                'CHEMBL_CSV = DATA_DIR / "chembl_clean.csv"',
                'CHEMBL_CSV = ANALISIS_ROOT / "data/processed/compounds_features.csv"',
            )
            text = text.replace(
                'CHEMBL_MODELS_DIR = PROJECT_ROOT / "outputs" / "chembl" / "models"',
                'CHEMBL_MODELS_DIR = ANALISIS_ROOT / "outputs" / "chembl" / "models"',
            )
            text = text.replace(
                'CHEMBL_METRICS = PROJECT_ROOT / "outputs" / "chembl" / "results" / "metrics_summary.csv"',
                'CHEMBL_METRICS = ANALISIS_ROOT / "outputs" / "chembl" / "results" / "stats_tests.csv"',
            )
            text = text.replace(
                'GEOJSON_PATH = DATA_DIR / "panama_distritos_merged.geojson"',
                'GEOJSON_PATH = ANALISIS_ROOT / "data/processed/panama_distritos_merged.geojson"',
            )
            text = text.replace(
                'ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "dashboard"',
                'ARTIFACTS_DIR = ANALISIS_ROOT / "outputs" / "dashboard"',
            )
            text = text.replace(
                'return not CHEMBL_CSV.is_file() and (BUNDLE_DIR / "chembl_clean.csv").is_file()',
                'return not CHEMBL_CSV.is_file() and (BUNDLE_DIR / "compounds_features.csv").is_file()',
            )
            jic_viz_config.write_text(text, encoding="utf-8")
            print("  patched viz/config.py (JIC)")


def patch_notebooks() -> None:
    print("=== Patching notebooks ===")
    root_setup = '''ROOT = Path(__file__).resolve().parents[1] if "__file__" in dir() else (
    Path.cwd() if (Path.cwd() / "src" / "analisis_proyecto").exists() else Path.cwd().parent
)
if not (ROOT / "src" / "analisis_proyecto").exists():
    ROOT = Path.cwd().parent if (Path.cwd().parent / "src" / "analisis_proyecto").exists() else Path.cwd()
'''
    # Simpler notebook root for all notebooks in proyecto analisis/notebooks
    nb_root = '''from src.paths import PROJECT_ROOT as ROOT, setup_path
setup_path()
'''
    for nb in PA.glob("notebooks/*.ipynb"):
        import json

        data = json.loads(nb.read_text(encoding="utf-8"))
        changed = False
        for cell in data.get("cells", []):
            if cell.get("cell_type") != "code":
                src = "".join(cell.get("source", []))
                if "../../docs/analisis_proyecto" in src:
                    cell["source"] = [ln.replace("../../docs/analisis_proyecto", "../docs") for ln in cell["source"]]
                    changed = True
                continue
            src = "".join(cell.get("source", []))
            new_src = src
            new_src = new_src.replace(
                "from src.data.pubchem_api import MIDA_ACTIVE_INGREDIENTS",
                "from src.data.mida import MIDA_ACTIVE_INGREDIENTS",
            )
            new_src = new_src.replace("../../docs/analisis_proyecto/", "../docs/")
            new_src = re.sub(
                r"ROOT = Path\.cwd\(\)\.parent\.parent if.*?else Path\.cwd\(\)\s*\)",
                "from src.paths import PROJECT_ROOT as ROOT, setup_path\nsetup_path()",
                new_src,
                flags=re.DOTALL,
            )
            new_src = new_src.replace(
                'CLEAN_CSV = ROOT / "data" / "processed" / "chembl_clean.csv"',
                'ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"\nCOMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"',
            )
            if new_src != src:
                cell["source"] = [line + "\n" for line in new_src.splitlines()]
                if cell["source"]:
                    cell["source"][-1] = cell["source"][-1].rstrip("\n")
                changed = True
        if changed:
            nb.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  patched {nb.relative_to(MONOREPO)}")


def patch_jic_files() -> None:
    print("=== Patching JIC root files ===")
    # Remove analytics router from JIC app if analytics moved
    app_path = MONOREPO / "viz" / "app.py"
    if app_path.is_file():
        text = app_path.read_text(encoding="utf-8")
        if "analytics_router" in text:
            text = text.replace("from viz.routes.analytics import router as analytics_router\n", "")
            text = text.replace("app.include_router(analytics_router)\n", "")
            text = text.replace(
                "Visor GNN-GIN/XAI + analytics ChEMBL y Panamá",
                "Visor GNN-GIN/XAI (analytics ChEMBL → proyecto analisis/viz/)",
            )
            app_path.write_text(text, encoding="utf-8")
            print("  patched viz/app.py — analytics desacoplado")

    # src/__init__.py
    init = MONOREPO / "src" / "__init__.py"
    if init.is_file():
        text = init.read_text(encoding="utf-8")
        text = text.replace("analisis_proyecto", "proyecto analisis (movido)")
        init.write_text(text, encoding="utf-8")

    # config.yaml — remove chembl section note
    cfg = MONOREPO / "config" / "config.yaml"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8")
        if "chembl:" in text:
            text = re.sub(r"\n# ChEMBL.*?exclude_validity_comment: true\n", "\n", text, flags=re.DOTALL)
            cfg.write_text(text, encoding="utf-8")
            print("  removed chembl section from root config.yaml")

    # Makefile
    mk = MONOREPO / "Makefile"
    if mk.is_file():
        text = mk.read_text(encoding="utf-8")
        text = text.replace("CHEMBL_HOST_DIR := data/external/chembl", 'CHEMBL_HOST_DIR := proyecto analisis/data/external/chembl')
        text = text.replace(
            'CHEMBL_NOTEBOOK := notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb',
            'CHEMBL_NOTEBOOK := proyecto analisis/notebooks/fase1_adquisicion.ipynb',
        )
        text = text.replace("scripts/analisis_proyecto/", "proyecto analisis/scripts/")
        text = text.replace(
            'prepare-dashboard:\n\t"$(VENV_PYTHON)" scripts/fase5/prepare_dashboard.py',
            'prepare-dashboard:\n\t"$(VENV_PYTHON)" "proyecto analisis/scripts/fase5/prepare_dashboard.py"',
        )
        text = text.replace(
            'prepare-dashboard-bundle:\n\t"$(VENV_PYTHON)" scripts/fase5/prepare_dashboard.py --bundle',
            'prepare-dashboard-bundle:\n\t"$(VENV_PYTHON)" "proyecto analisis/scripts/fase5/prepare_dashboard.py" --bundle',
        )
        if "analisis-viz:" not in text:
            text += '''
# ── Proyecto análisis (ChEMBL) — visor standalone ───────────────────────────
analisis-viz:
\t"$(VENV_PYTHON)" -m uvicorn viz.app:app --app-dir "proyecto analisis" --host 127.0.0.1 --port 8001 --reload

analisis-verify:
\t"$(VENV_PYTHON)" "proyecto analisis/scripts/fase4/verify_flow_b.py"
'''
        mk.write_text(text, encoding="utf-8")
        print("  patched Makefile")

    # docker compose for chembl — copy to proyecto analisis
    compose_src = MONOREPO / "docker" / "docker-compose.yml"
    compose_dst = PA / "docker" / "docker-compose.yml"
    if compose_src.is_file() and not compose_dst.is_file():
        text = compose_src.read_text(encoding="utf-8")
        text = text.replace("context: ..", "context: ../..")
        text = text.replace("dockerfile: docker/Dockerfile", "dockerfile: docker/Dockerfile")
        text = text.replace("- ../data:/app/data", '- ../../proyecto analisis/data:/app/data')
        text = text.replace("- ../outputs:/app/outputs", '- ../../proyecto analisis/outputs:/app/outputs')
        text = text.replace("- ../notebooks:/app/notebooks", '- ../../proyecto analisis/notebooks:/app/notebooks')
        text = text.replace(
            'python scripts/analisis_proyecto/fase1/verify_chembl_db.py',
            'python scripts/fase1/verify_chembl_db.py',
        )
        compose_dst.write_text(text, encoding="utf-8")
        print("  wrote proyecto analisis/docker/docker-compose.yml")

    # Update write_opcion_a_notebooks paths
    wnb = PA / "scripts" / "write_opcion_a_notebooks.py"
    if wnb.is_file():
        patch_file(wnb, [
            ('NB_DIR = ROOT / "notebooks" / "proyecto analisis de datos"', 'NB_DIR = ROOT / "notebooks"'),
            ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parents[1]"),
        ])


def rewrite_notebook_configs() -> None:
    """Regenera celdas de configuración con paths del nuevo layout."""
    import json

    config_cell = '''import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import Image, display

from src.paths import PROJECT_ROOT as ROOT, setup_path
setup_path()

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.05)
plt.rcParams.update({"figure.figsize": (10, 5), "figure.dpi": 120})

FIG_DIR = ROOT / "outputs" / "chembl" / "figures"
RESULTS_DIR = ROOT / "outputs" / "chembl" / "results"
for d in (FIG_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)
'''
    for nb_path in PA.glob("notebooks/fase*.ipynb"):
        data = json.loads(nb_path.read_text(encoding="utf-8"))
        for i, cell in enumerate(data["cells"]):
            if cell["cell_type"] == "code" and "setup_path()" in "".join(cell.get("source", [])):
                # already patched
                break
            if cell["cell_type"] == "code" and "import sys" in "".join(cell.get("source", []))[:200]:
                # replace config cell - keep imports from preprocessing after ROOT block
                old = "".join(cell["source"])
                if "from src.analisis_proyecto" in old or "from src.paths" in old:
                    lines = old.splitlines()
                    tail = [ln for ln in lines if ln.strip().startswith("from src.analisis_proyecto") or ln.strip().startswith("from src.analisis") or "CSV" in ln or "assert" in ln or "RAW" in ln or "load_" in ln or "print(" in ln or "display(" in ln]
                    if not tail:
                        tail = [ln for ln in lines if ln.startswith("from src.") or "CSV" in ln or "assert" in ln]
                    cell["source"] = [config_cell + "\n"] + [ln + "\n" for ln in tail if ln + "\n" != config_cell]
                break
        nb_path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    print(f"Migrating to {PA}")
    mkdirs()
    move_trees()
    write_paths_module()
    write_mida_module()
    write_config()
    write_viz_app()
    write_requirements()
    write_readme()
    patch_python_files()
    patch_notebooks()
    patch_jic_files()
    print("=== Migration complete ===")


if __name__ == "__main__":
    main()
