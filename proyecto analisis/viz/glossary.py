"""Glosario en español de columnas y métricas del proyecto.

Cada entrada: {"es": título legible, "desc": explicación en español, "ej": ejemplo}.
Se sirve al frontend vía /api/analytics/glossary para:
  - poner encabezados de tabla legibles (en vez de 'mw_freebase')
  - una tabla desplegable que explica cada columna/métrica.
"""
from __future__ import annotations

# ── Columnas de datos ────────────────────────────────────────────────────────
COLUMNS: dict[str, dict[str, str]] = {
    # Identificación
    "compound_name": {"es": "Compuesto", "desc": "Nombre del plaguicida / compuesto.", "ej": "Atrazine"},
    "chembl_id": {"es": "ID ChEMBL", "desc": "Identificador único de la molécula en ChEMBL.", "ej": "CHEMBL15063"},
    "pubchem_cid": {"es": "CID PubChem", "desc": "Identificador de la molécula en PubChem.", "ej": "2256"},
    "family": {"es": "Familia química", "desc": "Familia a la que pertenece el plaguicida (define su mecanismo).", "ej": "Triazines"},
    "smiles": {"es": "SMILES", "desc": "Estructura de la molécula escrita como texto.", "ej": "CCNc1nc(Cl)nc(NC(C)C)n1"},
    "match_method": {"es": "Método de match", "desc": "Cómo se resolvió el ID de ChEMBL (SMILES, nombre, registro).", "ej": "sqlite_smiles"},
    # Medición (nivel experimento)
    "activity_id": {"es": "ID medición", "desc": "Identificador único de cada medición experimental.", "ej": "1234567"},
    "standard_type": {"es": "Tipo de ensayo", "desc": "Qué magnitud se midió (IC50, Ki, LD50…). No todas son comparables.", "ej": "IC50"},
    "standard_relation": {"es": "Relación", "desc": "= valor exacto; > o < valor censurado (no se llegó a ver el efecto).", "ej": "="},
    "standard_value": {"es": "Valor medido", "desc": "Concentración/dosis medida, en sus unidades originales.", "ej": "930"},
    "standard_units": {"es": "Unidades", "desc": "Unidad del valor medido.", "ej": "nM"},
    "pchembl_value": {"es": "pChEMBL", "desc": "Potencia en escala −log10(molar). Más alto = más potente. 6 = 1 µM.", "ej": "6.03"},
    "pchembl_imputed": {"es": "pChEMBL imputado", "desc": "Verdadero si el pChEMBL se recalculó desde el valor y la unidad.", "ej": "False"},
    "is_censored": {"es": "Censurado", "desc": "Verdadero si la relación no es '=' (valor > o <). Se excluye de la potencia.", "ej": "False"},
    "activity_class": {"es": "Clase de actividad", "desc": "Activo (pChEMBL ≥ 6) o Inactivo. Uso descriptivo, no es objetivo del modelo.", "ej": "Active"},
    "assay_type": {"es": "Tipo de ensayo (assay)", "desc": "Naturaleza del experimento: unión (B), funcional (F), ADMET (A).", "ej": "B"},
    # Diana
    "target_chembl_id": {"es": "ID diana", "desc": "Identificador de la diana biológica en ChEMBL.", "ej": "CHEMBL2003"},
    "target_name": {"es": "Diana", "desc": "Nombre de la diana biológica (proteína, organismo…) contra la que se midió.", "ej": "Acetylcholinesterase"},
    "target_type": {"es": "Tipo de diana", "desc": "Proteína única, organismo entero, línea celular, etc.", "ej": "SINGLE PROTEIN"},
    # Descriptores moleculares
    "mw_freebase": {"es": "Peso molecular (Da)", "desc": "Qué tan grande y pesada es la molécula.", "ej": "215.7"},
    "alogp": {"es": "Lipofilia (LogP)", "desc": "Qué tan 'grasosa' vs 'acuosa' es. Alto = se acumula en grasa.", "ej": "2.6"},
    "psa": {"es": "Área polar (Å²)", "desc": "Superficie que interactúa con el agua. Alta = cuesta cruzar membranas.", "ej": "62.7"},
    "hba": {"es": "Aceptores de H", "desc": "Puentes de hidrógeno que la molécula puede aceptar (O, N).", "ej": "5"},
    "hbd": {"es": "Donores de H", "desc": "Puentes de hidrógeno que puede donar (–OH, –NH).", "ej": "2"},
    "aromatic_rings": {"es": "Anillos aromáticos", "desc": "Nº de anillos estables tipo benceno.", "ej": "1"},
    "rtb": {"es": "Enlaces rotables", "desc": "Qué tan flexible es la molécula (cuánto puede doblarse).", "ej": "4"},
    "num_ro5_violations": {"es": "Violaciones Ro5", "desc": "Violaciones de la regla de Lipinski (0 = 'apta como fármaco').", "ej": "0"},
    "heavy_atoms": {"es": "Átomos pesados", "desc": "Nº de átomos sin contar hidrógenos (correlaciona con el peso).", "ej": "15"},
    # Agregados por compuesto
    "pchembl_median_binding": {"es": "Potencia mediana", "desc": "Mediana del pChEMBL sobre ensayos de unión no censurados. Resumen de potencia del compuesto.", "ej": "5.4"},
    "pchembl_std_binding": {"es": "Desviación de potencia", "desc": "Dispersión del pChEMBL entre sus mediciones de unión.", "ej": "0.8"},
    "pchembl_iqr_binding": {"es": "Rango intercuartil potencia", "desc": "Amplitud central (Q3−Q1) de la potencia.", "ej": "1.1"},
    "n_activities_total": {"es": "Nº mediciones", "desc": "Cuántos experimentos totales tiene el compuesto.", "ej": "34"},
    "n_activities_binding": {"es": "Nº mediciones de unión", "desc": "Cuántas mediciones de unión (usadas para la potencia).", "ej": "8"},
    "n_censored": {"es": "Nº censuradas", "desc": "Cuántas mediciones del compuesto son censuradas (>, <).", "ej": "5"},
    "reliability_tier": {"es": "Confiabilidad", "desc": "Nivel de soporte de la potencia según cuántas mediciones de unión tiene.", "ej": "media"},
    "target_inestable": {"es": "Potencia inestable", "desc": "Verdadero si la potencia varía mucho entre dianas (desviación > 1).", "ej": "False"},
    "pct_active": {"es": "% activo", "desc": "Fracción de mediciones del compuesto que caen del lado Activo.", "ej": "0.62"},
    "has_quantitative_potency": {"es": "Tiene potencia útil", "desc": "Verdadero si tiene ≥3 mediciones de unión (entra al análisis de potencia).", "ej": "True"},
    "mixed_endpoint_class": {"es": "Endpoints mixtos", "desc": "Verdadero si mezcla ensayos de unión y de organismo.", "ej": "True"},
    "endpoint_types_seen": {"es": "Endpoints vistos", "desc": "Tipos de ensayo distintos que tiene el compuesto.", "ej": "IC50, Potency"},
    "cluster": {"es": "Cluster", "desc": "Grupo asignado por K-means en el espacio fisicoquímico (Fase 4).", "ej": "1"},
}

# ── Métricas (modelado / estadística) ────────────────────────────────────────
METRICS: dict[str, dict[str, str]] = {
    "r2": {"es": "R² (bondad de ajuste)", "desc": "Qué tan bien el modelo explica la potencia. 1 = perfecto, 0 = igual que predecir la media, negativo = PEOR que la media."},
    "r2_cv_mean": {"es": "R² medio (CV)", "desc": "R² promedio entre los pliegues de validación cruzada."},
    "r2_cv_std": {"es": "Desviación del R²", "desc": "Cuánto varía el R² entre pliegues (inestabilidad)."},
    "mae": {"es": "Error absoluto medio (MAE)", "desc": "Error promedio de la predicción, en unidades de pChEMBL."},
    "rmse": {"es": "Error cuadrático (RMSE)", "desc": "Error típico penalizando los grandes, en pChEMBL."},
    "silhouette": {"es": "Silueta", "desc": "Qué tan separados/compactos son los clusters. Cerca de 1 = buena estructura; cerca de 0 = débil."},
    "ari": {"es": "ARI vs familia", "desc": "Acuerdo entre los clusters y las familias químicas. 1 = idénticos, 0 = azar."},
    "epsilon2": {"es": "Tamaño de efecto (ε²)", "desc": "Magnitud de la diferencia entre familias. >0.14 grande, ~0.06 mediano, <0.01 nulo."},
    "p_adjusted": {"es": "p ajustado (FDR)", "desc": "Significancia corregida por múltiples pruebas. <0.05 = diferencia significativa."},
    "pca_var": {"es": "Varianza explicada (PCA)", "desc": "Cuánta información del espacio conservan las 2 primeras componentes."},
    "leak": {"es": "Con fuga de datos", "desc": "Split por filas: la misma molécula cae en train y test → métrica inflada, engañosa."},
    "honest": {"es": "Sin fuga (por grupos)", "desc": "Cada molécula en un solo pliegue: mide generalización real."},
    "compound": {"es": "Por compuesto", "desc": "Predice la potencia mediana de compuestos no vistos."},
}


def label(col: str) -> str:
    """Título legible de una columna (fallback: el propio nombre)."""
    return COLUMNS.get(col, {}).get("es", col)


def payload() -> dict:
    """Estructura para el endpoint /api/analytics/glossary."""
    return {"columns": COLUMNS, "metrics": METRICS}
