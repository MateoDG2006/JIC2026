"""Pipeline de análisis ChEMBL — módulos por fase.

Subpaquetes:
  core/          — constantes (JSON) y modelos tipados
  acquisition/   — Fase 1: extracción ChEMBL vía chembl-server
  preprocessing/ — Fases 2–3: limpieza, features, EDA
  modeling/      — Fase 4: PCA, clustering, baseline P6
"""

from src.analisis_proyecto.acquisition.extract import ChemblExtractor
from src.analisis_proyecto.modeling.baseline import CompoundLevelBaseline, RowLevelSplitContrast
from src.analisis_proyecto.preprocessing.pipeline import load_bioactivity

__all__ = [
    "ChemblExtractor",
    "CompoundLevelBaseline",
    "RowLevelSplitContrast",
    "load_bioactivity",
]
