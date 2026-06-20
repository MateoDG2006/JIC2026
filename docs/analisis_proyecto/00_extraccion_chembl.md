# Etapa 00 — Extracción de datos ChEMBL (Flujo A)

## Objetivo

Construir un dataset tabular de **bioactividad** para los **20 ingredientes activos del MIDA** (Panamá), descargado desde [ChEMBL](https://www.ebi.ac.uk/chembl/). Este dataset alimenta el análisis clásico del curso (EDA, modelos sklearn, dashboard Dash) sin modificar el pipeline GNN/Tox21 del proyecto JIC.

**Pregunta que responde esta etapa:** *¿Qué registros de bioactividad y propiedades moleculares existen en ChEMBL para los plaguicidas panameños prioritarios?*

---

## Relación con el proyecto JIC

| Componente | Fuente | Rol |
|---|---|---|
| Entrenamiento GNN-GIN | Tox21 (~8000 compuestos) | Modelo principal de toxicidad multitarea |
| Corpus Panamá | PubChem (MIDA + familias HNID) | Aplicación y validación GHS |
| **ChEMBL (esta etapa)** | EMBL-EBI | Dataset tabular para el curso de Análisis de Datos |

Los tres comparten el dominio (bioactividad de agroquímicos) pero son pipelines independientes.

---

## Artefactos

| Archivo | Descripción |
|---|---|
| `notebooks/proyecto analisis de datos/00_chembl_extraccion.ipynb` | Notebook ejecutable del flujo |
| `src/analisis_proyecto/chembl_api.py` | Cliente REST + extracción SQLite offline |
| `src/analisis_proyecto/chembl_extract.py` | Fachada unificada Flujo A |
| `data/raw/chembl_mida_compounds.csv` | 20 compuestos filtrados |
| `data/raw/chembl_mida_mapping.csv` | Mapeo PubChem → ChEMBL |
| `data/raw/chembl_panama_bioactivity_raw.csv` | Actividades sin filtrar calidad |
| `data/raw/chembl_panama_bioactivity.csv` | Dataset listo para Flujo B |
| `outputs/chembl/*.png` | Figuras de resumen de extracción |

---

## Pipeline

```
pubchem_panama_cids.csv
        │
        ▼  Filtrar source == MIDA_name_search (20 compuestos)
chembl_mida_compounds.csv
        │
        ▼  Resolver molecule_chembl_id (cascada)
chembl_mida_mapping.csv
        │
        ▼  Descargar actividades IC50 / EC50 / Ki
        ▼  Enriquecer: molécula, diana, ensayo
chembl_panama_bioactivity_raw.csv
        │
        ▼  Filtros de calidad + activity_class
chembl_panama_bioactivity.csv
```

---

## Paso 1 — Filtrado MIDA

Se parte de `data/raw/pubchem_panama_cids.csv`, que mezcla ~20 ingredientes MIDA con ~217 compuestos de familias HNID. Solo se conservan los MIDA:

```python
mida = corpus[
    (corpus["source"] == "MIDA_name_search")
    & (corpus["name"].isin(MIDA_ACTIVE_INGREDIENTS))
]
```

Cada compuesto recibe una **familia química** manual (`MIDA_FAMILY_MAP` en `chembl_api.py`), porque en PubChem todos aparecen como `family = mixed`.

### Los 20 ingredientes

| Familia | Compuestos |
|---|---|
| Organophosphates | Chlorpyrifos, Malathion, Dimethoate, Methyl parathion |
| Carbamates | Carbaryl, Methomyl, Aldicarb |
| Triazines | Atrazine, Simazine |
| Azole_fungicides | Tebuconazole, Propiconazole, Difenoconazole |
| Pyrethroids | Cypermethrin, Deltamethrin, Lambda-cyhalothrin |
| Herbicides | Glyphosate, Paraquat, 2,4-D |
| Fungicides | Mancozeb, Chlorothalonil |

---

## Paso 2 — Mapeo ChEMBL ID

Estrategia en cascada (API REST `https://www.ebi.ac.uk/chembl/api/data`):

1. **PubChem xref** — `molecule_cross_references` con CID
2. **SMILES** — `molecule_structures__canonical_smiles__flexmatch`
3. **pref_name** — nombre exacto del compuesto
4. **sinónimo** — `molecule_synonyms__molecule_synonym__iexact`

Si no hay match, se guarda `chembl_id = NaN` para **trazabilidad** (no se omiten filas del mapping).

| Campo | Significado |
|---|---|
| `match_method` | Estrategia que funcionó (`pubchem_xref`, `smiles`, etc.) |
| `match_status` | `ok`, `ambiguous`, `not_found` |
| `n_candidates` | Cuántos registros ChEMBL coincidieron |

### Casos especiales

- **Mancozeb:** mezcla polimérica Mn/Zn; puede no tener un único `molecule_chembl_id`.
- **Paraquat / Glyphosate:** catión o sales; el match por SMILES suele ser el más fiable.

---

## Paso 3 — Descarga de bioactividad (raw)

Por cada `molecule_chembl_id` válido se descargan actividades con:

- `standard_type` ∈ {IC50, EC50, Ki}
- **Sin filtrar** en esta etapa: `standard_relation`, `data_validity_comment`, `pchembl_value` nulo

Esto permite documentar cuántos registros se excluyen después.

Campos enriquecidos por fila:

- **Actividad:** `standard_value`, `pchembl_value`, `standard_relation`, comentarios de validez
- **Diana:** `target_name`, `target_type`, `organism`
- **Ensayo:** `assay_type`, `bao_label`
- **Molécula:** MW, LogP, PSA, HBA, HBD, anillos aromáticos, etc.

---

## Paso 4 — Variable `activity_class`

| Clase | Criterio |
|---|---|
| **Active** | `pchembl_value >= 6.0` (equivalente a IC50 ≤ 1 µM) |
| **Inactive** | `pchembl_value < 6.0` |
| **NaN** | Sin pChEMBL calculado |

El umbral 6.0 es el estándar ChEMBL para considerar un compuesto biológicamente activo.

---

## Paso 5 — Filtros de calidad

Se aplican sobre el dataset raw y se documentan los conteos:

| Regla | Acción |
|---|---|
| `pchembl_value` nulo | Excluir |
| `standard_relation != '='` | Excluir (valores censurados: `>`, `<`) |
| `data_validity_comment` no nulo | Excluir (dato marcado como dudoso por ChEMBL) |

El CSV **raw** se conserva; el CSV **limpio** (`chembl_panama_bioactivity.csv`) es la entrada del Flujo B.

---

## Implementación técnica

### Cliente REST (no `chembl_webresource_client`)

El paquete `chembl_webresource_client` falla si el endpoint `/spore` de EBI devuelve HTTP 500 al importar. La implementación usa `requests` con:

- 4 reintentos con backoff (`RETRY_DELAY = 2.5 s`)
- Paginación automática (`limit=1000`, `offset` incremental)

```python
from src.analisis_proyecto.chembl_api import (
    load_mida_compounds,
    build_mapping_table,
    build_bioactivity_table,
    apply_quality_filters,
)
```

### Funciones principales (`src/analisis_proyecto/`)

| Función | Rol |
|---|---|
| `load_mida_compounds()` | Filtra 20 MIDA desde PubChem CSV |
| `resolve_chembl_id()` | Mapeo en cascada por compuesto |
| `build_mapping_table()` | Tabla de mapping para los 20 |
| `fetch_activities_raw()` | Descarga IC50/EC50/Ki paginada |
| `build_bioactivity_table()` | Tabla larga enriquecida |
| `derive_activity_class()` | Active / Inactive |
| `apply_quality_filters()` | Filtros + tabla de exclusión |

---

## Cómo ejecutar

### Requisitos

```bash
# Desde la raíz del repo, con .venv activo
pip install -r requirements.txt
```

Dependencias clave: `pandas`, `requests`, `rdkit`, `matplotlib`, `seaborn`.

### Notebook

```bash
jupyter notebook "notebooks/proyecto analisis de datos/00_chembl_extraccion.ipynb"
```

**Prerequisito:** `data/raw/pubchem_panama_cids.csv` (generado con `make build-panama-corpus` o equivalente).

**Tiempo estimado:** 5–15 minutos (20 compuestos × API REST + paginación de actividades).

### Verificación rápida

```bash
python -c "
from pathlib import Path
from src.analisis_proyecto.chembl_api import resolve_chembl_id
m = resolve_chembl_id('Chlorpyrifos', 2730, 'CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl')
print(m)
"
```

---

## Columnas del dataset final

| Columna | Tipo | Descripción |
|---|---|---|
| `compound_name` | str | Nombre del plaguicida |
| `chembl_id` | str | ID ChEMBL |
| `smiles` | str | SMILES canónico |
| `family` | cat | Familia química |
| `target_name` | str | Diana biológica del ensayo |
| `standard_type` | cat | IC50, EC50, Ki |
| `standard_value` | float | Valor en nM |
| `pchembl_value` | float | **Objetivo regresión** |
| `activity_class` | cat | **Objetivo clasificación** (Active/Inactive) |
| `mw_freebase`, `alogp`, `psa`, … | float/int | Descriptores moleculares |

Lista completa en `BIOACTIVITY_COLUMNS` dentro de `src/analisis_proyecto/`.

---

## Siguiente etapa

→ [01_analisis_datos_chembl.md](01_analisis_datos_chembl.md) — EDA, imputación, correlación, clasificación y regresión sobre `chembl_panama_bioactivity.csv`.
