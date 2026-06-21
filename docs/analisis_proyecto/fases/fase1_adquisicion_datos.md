# Fase 1 — Adquisicion y Extraccion de Datos (Flujo A)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Construir dataset tabular de bioactividad para 20 ingredientes activos MIDA desde ChEMBL |
| **Duracion** | 3-4 dias |
| **Entrada** | `data/raw/pubchem_panama_cids.csv` (235 compuestos PubChem) |
| **Salida principal** | `data/raw/chembl_panama_bioactivity.csv` (3,608 registros limpios) |
| **Rol lider** | Ingeniero de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb` |
| **Comando** | `make chembl-extract` |

---

## 1. Contexto y justificacion

El proyecto JIC tiene su propio pipeline de datos (Tox21 via DeepChem/PubChem), pero el curso de Analisis de Datos requiere un dataset **tabular** con variables numericas, categoricas y faltantes. ChEMBL proporciona exactamente eso: bioactividad experimental de los mismos plaguicidas del proyecto JIC, pero en formato relacional con descriptores moleculares precalculados.

**Pregunta que responde esta fase:** Que registros de bioactividad y propiedades moleculares existen en ChEMBL para los plaguicidas panameños prioritarios?

### Relacion con el proyecto JIC

El repositorio mantiene tres pipelines de datos independientes pero tematicamente coherentes:

| Componente | Fuente | Rol |
|---|---|---|
| Entrenamiento GNN-GIN | Tox21 (~8000 compuestos) | Modelo principal de toxicidad multitarea |
| Corpus Panama | PubChem (MIDA + familias HNID) | Aplicacion y validacion GHS |
| **ChEMBL (esta fase)** | EMBL-EBI | Dataset tabular para el curso de Analisis de Datos |

Los tres comparten el dominio (bioactividad de agroquimicos) pero NO comparten artefactos: ChEMBL alimenta el flujo clasico (EDA, sklearn, dashboard) sin tocar el pipeline GNN/Tox21.

---

## 2. Los 20 ingredientes activos del MIDA

| Familia | Compuestos | ChEMBL IDs conocidos |
|---|---|---|
| Organophosphates | Chlorpyrifos, Malathion, Dimethoate, Methyl parathion | CHEMBL417, CHEMBL640, CHEMBL1085, CHEMBL263264 |
| Carbamates | Carbaryl, Methomyl, Aldicarb | CHEMBL1105, CHEMBL493874, CHEMBL471926 |
| Triazines | Atrazine, Simazine | CHEMBL15810, CHEMBL339542 |
| Azole_fungicides | Tebuconazole, Propiconazole, Difenoconazole | CHEMBL1553478, CHEMBL1292, CHEMBL1628581 |
| Pyrethroids | Cypermethrin, Deltamethrin, Lambda-cyhalothrin | CHEMBL389064, CHEMBL1545, CHEMBL1892001 |
| Herbicides | Glyphosate, Paraquat, 2,4-D | CHEMBL556, CHEMBL282020, CHEMBL519 |
| Fungicides | Mancozeb, Chlorothalonil | (polimero, problematico), CHEMBL44847 |

Estos IDs estan hardcodeados en `KNOWN_MIDA_CHEMBL_IDS` dentro de `chembl_api.py` (linea 31) para evitar llamadas API innecesarias.

---

## 3. Pipeline de extraccion

```
pubchem_panama_cids.csv (235 CIDs de PubChem)
     |
     v  PASO 1: Filtrar source == MIDA_name_search
chembl_mida_compounds.csv (20 compuestos)
     |
     v  PASO 2: Resolucion cascada PubChem -> ChEMBL ID
chembl_mida_mapping.csv (20 filas con match_method y match_status)
     |
     v  PASO 3: Descarga bioactividad por ChEMBL ID
     v  13 tipos de ensayo: IC50, EC50, Ki, Kd, Potency, Inhibition,
     v  AC50, LC50, GI50, MIC, LD50, ED50, IC90
     |
     v  PASO 4: Enriquecimiento con diana, ensayo, descriptores moleculares
chembl_panama_bioactivity_raw.csv (10,745 registros)
     |
     v  PASO 5: Filtros de calidad + derivacion activity_class
chembl_panama_bioactivity.csv (3,608 registros)
```

---

## 4. Detalle de cada paso

### Paso 1 — Filtrado MIDA

**Funcion:** `load_mida_compounds(corpus_path)` en `chembl_api.py:342`

```python
# Filtra del corpus PubChem solo los 20 ingredientes MIDA
mida = corpus[
    (corpus["source"] == "MIDA_name_search")
    & (corpus["name"].isin(MIDA_ACTIVE_INGREDIENTS))
]
```

Cada compuesto recibe una familia quimica del diccionario `MIDA_FAMILY_MAP` (linea 70), porque en PubChem todos aparecen como `family = mixed`.

**Salida:** `data/raw/chembl_mida_compounds.csv` (20 filas)

| Columna | Tipo | Ejemplo |
|---|---|---|
| compound_name | str | Chlorpyrifos |
| pubchem_cid | int | 2730 |
| smiles | str | CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl |
| family | str | Organophosphates |
| source | str | MIDA_name_search |
| is_mida | bool | True |

### Paso 2 — Resolucion ChEMBL ID (cascada)

**Funcion:** `resolve_chembl_id(compound_name, pubchem_cid, smiles)` en `chembl_api.py:426`

Estrategia de resolucion en 5 niveles:

| Nivel | Metodo | Endpoint ChEMBL | Criterio |
|---|---|---|---|
| 0 | known_registry | — | Lookup en `KNOWN_MIDA_CHEMBL_IDS` (sin API) |
| 1 | pubchem_xref | `/molecule?molecule_cross_references__xref_id=` | CID de PubChem |
| 2 | smiles | `/molecule?molecule_structures__canonical_smiles__flexmatch=` | SMILES canonico RDKit |
| 3 | pref_name | `/molecule?pref_name__iexact=` | Nombre exacto |
| 4 | synonym | `/molecule?molecule_synonyms__molecule_synonym__iexact=` | Sinonimo registrado |

Si multiples candidatos, `_pick_best_match()` (linea 413) prioriza moleculas con mayor conteo de actividades y tipo `MOL` sobre `UNKNOWN`.

**Backend SQLite alternativo:** `resolve_chembl_id_local()` en `chembl_local.py:139` ejecuta las mismas estrategias via SQL contra `chembl_37.db`:

```sql
SELECT DISTINCT md.chembl_id
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE cs.canonical_smiles = ?
```

**Salida:** `data/raw/chembl_mida_mapping.csv`

| Columna | Significado |
|---|---|
| compound_name | Nombre del plaguicida |
| pubchem_cid | CID de PubChem |
| smiles | SMILES canonico |
| family | Familia quimica |
| chembl_id | ID ChEMBL resuelto |
| match_method | Estrategia que funciono |
| match_status | ok, ambiguous, not_found |
| n_candidates | Cuantos ChEMBL IDs coincidieron |
| chembl_pref_name | Nombre preferido en ChEMBL |

### Paso 3 — Descarga de bioactividad

**Funcion:** `fetch_activities_raw(chembl_id, sleep_s, standard_types)` en `chembl_api.py:631`

Por cada `molecule_chembl_id` valido, descarga actividades con paginacion automatica:

```python
for st in standard_types:
    params = {
        "molecule_chembl_id": chembl_id,
        "standard_type": st,
        "limit": 1000,
    }
    records = _fetch_paginated("activity", params, page_limit=5)
```

**Backend SQLite:** `fetch_activities_local()` en `chembl_local.py:387` ejecuta un `UNION ALL` de queries SQL con 13 `standard_type` en una sola conexion.

**Campos descargados por registro:**

| Grupo | Campos |
|---|---|
| Actividad | activity_id, standard_type, standard_value, standard_units, standard_relation, pchembl_value, data_validity_comment, activity_comment |
| Diana | target_chembl_id, target_name, target_type, organism |
| Ensayo | assay_chembl_id, assay_type, bao_label |
| Molecula | mw_freebase, alogp, psa, hba, hbd, aromatic_rings, heavy_atoms, rtb, num_ro5_violations, cx_logp, cx_logd, molecular_species |

### Paso 4 — Derivacion de activity_class

**Funcion:** `derive_activity_class(df, threshold=6.0)` en `chembl_api.py:901`

| Clase | Criterio | Significado |
|---|---|---|
| Active | pchembl_value >= 6.0 | IC50 <= 1 uM (biologicamente activo) |
| Inactive | pchembl_value < 6.0 | IC50 > 1 uM |
| NaN | Sin pChEMBL | No evaluable |

**Imputacion de pChEMBL faltante:** `impute_pchembl_value()` (linea 873) calcula `pChEMBL = -log10(valor_en_molar)` cuando `standard_relation == '='` y el valor es convertible a molar.

```python
def compute_pchembl_from_standard_value(value, units):
    factor = _UNIT_TO_MOLAR.get(units)  # nM -> 1e-9, uM -> 1e-6, etc.
    if factor is None or value <= 0:
        return None
    molar = value * factor
    return round(-math.log10(molar), 2)
```

### Paso 5 — Filtros de calidad

**Funcion:** `apply_quality_filters(df)` en `chembl_api.py:914`

| Filtro | Accion | Registros tipicos eliminados |
|---|---|---|
| `pchembl_value` nulo | Excluir | ~40% del raw |
| `standard_relation != '='` | Excluir valores censurados (>, <) | ~15% |
| `data_validity_comment` presente | Excluir datos dudosos | ~5% |

El CSV raw se conserva intacto para auditoria. Solo el CSV limpio pasa a la Fase 2.

---

## 4.bis Notas de implementacion tecnica

### Por que no `chembl_webresource_client`

El paquete oficial `chembl_webresource_client` falla al importar si el endpoint `/spore` de EBI devuelve HTTP 500. La implementacion del proyecto evita esa dependencia y usa `requests` directamente con:

- 4 reintentos con backoff (`RETRY_DELAY = 2.5 s`)
- Paginacion automatica (`limit=1000`, `offset` incremental)
- Rate limiting respetuoso (`time.sleep(0.4)` entre familias)

```python
from src.analisis_proyecto.chembl_api import (
    load_mida_compounds,
    build_mapping_table,
    build_bioactivity_table,
    apply_quality_filters,
)
```

### Funciones principales (`src/analisis_proyecto/`)

| Funcion | Rol |
|---|---|
| `load_mida_compounds()` | Filtra 20 MIDA desde PubChem CSV |
| `resolve_chembl_id()` | Mapeo en cascada por compuesto |
| `build_mapping_table()` | Tabla de mapping para los 20 |
| `fetch_activities_raw()` | Descarga IC50/EC50/Ki paginada |
| `build_bioactivity_table()` | Tabla larga enriquecida |
| `derive_activity_class()` | Active / Inactive |
| `apply_quality_filters()` | Filtros + tabla de exclusion |

### Verificacion rapida desde terminal

```bash
# Confirmar que el mapeo de un compuesto resuelve correctamente
python -c "
from src.analisis_proyecto.chembl_api import resolve_chembl_id
m = resolve_chembl_id('Chlorpyrifos', 2730, 'CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl')
print(m)
"
```

Si la respuesta incluye `match_method` y un `chembl_id` valido, la cascada esta funcional.

---

## 5. Trabajo por rol

### Ingeniero de Datos (LIDER)

| # | Tarea | Archivo | Funcion clave |
|---|---|---|---|
| 1 | Configurar backend (sqlite/api) | `config/config.yaml` | Seccion `chembl:` |
| 2 | Implementar cliente REST | `chembl_api.py` | `_get_json()`, `_fetch_paginated()` |
| 3 | Implementar extraccion SQLite | `chembl_local.py` | `connect_readonly()`, `_bioactivity_sql()` |
| 4 | Crear facade unificada | `chembl_extract.py` | `build_mapping_table()`, `build_bioactivity_table()` |
| 5 | Mapeo cascada ChEMBL ID | `chembl_api.py` | `resolve_chembl_id()` |
| 6 | Descarga bioactividad | `chembl_api.py` | `fetch_activities_raw()` |
| 7 | Filtros de calidad | `chembl_api.py` | `apply_quality_filters()` |
| 8 | Derivar activity_class | `chembl_api.py` | `derive_activity_class()` |
| 9 | Imputar pChEMBL faltante | `chembl_api.py` | `impute_pchembl_value()` |
| 10 | Script de extraccion | `scripts/analisis_proyecto/fase1/extract_chembl_local.py` | `main()` |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Verificar integridad de DB | Ejecutar `make test-chembl` para validar que SQLite es legible |
| Documentar esquema de salida | Verificar que columnas coincidan con lo esperado por modelos downstream |
| Probar modo corpus completo | Ejecutar con `--corpus-mode full` (235 compuestos) vs `mida` (20) |

### Analista / Cientifico de Datos

No participan directamente. Reciben `chembl_panama_bioactivity.csv` como entrada.

---

## 6. Configuracion

### config/config.yaml (seccion chembl)

```yaml
chembl:
  backend: "sqlite"                    # sqlite (rapido, offline) o api (REST, lento)
  version: "37"
  db_path: "data/external/chembl/chembl_37.db"
  corpus_mode: "full"                  # full (235) o mida (20)
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
  pchembl_active_threshold: 6.0
  quality_filters:
    impute_pchembl: true
    require_exact_relation: true
    exclude_validity_comment: true
```

### Variables de entorno (opcionales)

| Variable | Efecto |
|---|---|
| `CHEMBL_BACKEND` | Override backend (sqlite/api) |
| `CHEMBL_DB_PATH` | Override ruta a chembl_37.db |
| `CHEMBL_VERSION` | Override version (e.g. "34") |
| `CHEMBL_CORPUS_MODE` | Override modo corpus (full/mida) |

---

## 7. Ejecucion

```bash
# Setup: descargar ChEMBL 37 via Docker (una vez, ~15 GB)
make setup-chembl

# Verificar que la DB es legible
make test-chembl

# Extraer bioactividad (SQLite, rapido)
make chembl-extract

# Alternativa: via API REST (lento, sin DB local)
make chembl-extract-api

# Alternativa: via Docker (aislado)
make chembl-extract-docker

# Ejecutar notebook interactivo
jupyter notebook "notebooks/proyecto analisis de datos/fase1_adquisicion.ipynb"
```

---

## 8. Salidas y volumenes esperados

| Archivo | Filas | Columnas | Tamano |
|---|---|---|---|
| `chembl_mida_compounds.csv` | 20 | 6 | ~2 KB |
| `chembl_mida_mapping.csv` | 20 | 9 | ~3 KB |
| `chembl_panama_bioactivity_raw.csv` | ~10,745 | 33 | ~5 MB |
| `chembl_panama_bioactivity.csv` | ~3,608 | 33 | ~2 MB |

---

## 9. Casos especiales

| Compuesto | Problema | Solucion |
|---|---|---|
| Mancozeb | Mezcla polimerica Mn/Zn, sin estructura unica | Match por sinonimo; puede tener 0 actividades |
| Paraquat | Cation libre vs sal; multiples CIDs | Match por SMILES del cation mas fiable |
| Glyphosate | Varias formas (acido, sal isopropilamina) | SMILES canonico resuelve |
| Lambda-cyhalothrin | Mezcla de isomeros | ChEMBL registra la mezcla racemica |

---

## 10. Criterios de exito

- [ ] 20 compuestos MIDA mapeados (>= 17 con match_status == ok)
- [ ] >= 3,000 registros de bioactividad post-filtros
- [ ] Todas las columnas documentadas presentes en el CSV final
- [ ] CSV raw conservado para auditoria
- [ ] Porcentaje de pChEMBL imputado documentado
- [ ] `make test-chembl` pasa sin errores

---

## 11. Diagrama de dependencias

```
config/config.yaml
     |
     v
src/analisis_proyecto/chembl_extract.py  (facade)
     |
     +---> chembl_local.py  (backend SQLite)
     |         |
     |         v
     |     data/external/chembl/chembl_37.db
     |
     +---> chembl_api.py    (backend REST)
               |
               v
           https://www.ebi.ac.uk/chembl/api/data/
```

---

*Siguiente fase:* [Fase 2 — Limpieza e ingenieria de datos](fase2_limpieza_datos.md)
