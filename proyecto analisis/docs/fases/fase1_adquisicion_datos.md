# Fase 1 — Adquisicion y Extraccion de Datos (Flujo A)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Construir dataset tabular de bioactividad para los 20 ingredientes activos MIDA desde ChEMBL |
| **Duracion** | 3-4 dias |
| **Entrada** | `data/raw/pubchem_panama_cids.csv` (235 compuestos PubChem) |
| **Salida principal** | `data/raw/chembl_panama_bioactivity.csv` (3,608 mediciones, ~107 compuestos unicos) |
| **Rol lider** | Ingeniero de Datos |
| **Notebook** | `notebooks/fase1_adquisicion.ipynb` |
| **Comando** | `make chembl-extract` |

---

## 1. Contexto y justificacion

El proyecto JIC tiene su propio pipeline de datos (Tox21 via DeepChem/PubChem), pero el curso de Analisis de Datos requiere un dataset **tabular** con variables numericas, categoricas y faltantes. ChEMBL proporciona exactamente eso: bioactividad experimental de los mismos plaguicidas del proyecto JIC, pero en formato relacional con descriptores moleculares precalculados.

**Pregunta que responde esta fase:** Que registros de bioactividad y propiedades moleculares existen en ChEMBL para los plaguicidas panameños prioritarios?

**Nota de alcance (importante):** esta fase resuelve la extraccion cruda. La decision de que se hace con esos datos ya no es predecir toxicidad con un modelo supervisado — esa via se intento y **fallo por diseno** (ver seccion 8.bis y [Fase 4 §12 — baseline P6](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6)). El dataset que sale de esta fase alimenta un analisis **descriptivo y multivariado** (Fases 3 y 4), con el compuesto como unidad de analisis. Por eso, desde esta fase en adelante se conservan explicitamente columnas de trazabilidad (`standard_relation`, `target_chembl_id`, `target_name`, `standard_type`) que antes se consideraban solo de paso y hoy son insumo directo de fases posteriores.

### Relacion con el proyecto JIC

El repositorio mantiene tres pipelines de datos independientes pero tematicamente coherentes:

| Componente | Fuente | Rol |
|---|---|---|
| Entrenamiento GNN-GIN | Tox21 (~8000 compuestos) | Modelo principal de toxicidad multitarea |
| Corpus Panama | PubChem (MIDA + familias HNID) | Aplicacion y validacion GHS |
| **ChEMBL (esta fase)** | EMBL-EBI | Caracterizacion tabular del corpus panameno + baseline honesto |

Los tres comparten el dominio (bioactividad de agroquimicos) pero NO comparten artefactos de entrenamiento. El rol de este flujo dentro del proyecto JIC cambio de "dataset de entrenamiento alternativo" a algo mas util dado el tamano real del corpus (~107 compuestos, ver 8.bis):

1. **Caracteriza el corpus panameno** que el GNN-GIN va a evaluar — perfil fisicoquimico, promiscuidad biologica, familias quimicas — con datos experimentales reales de ChEMBL, no solo con la estructura molecular.
2. **Aporta un baseline honesto**: al intentar predecir potencia/actividad con descriptores clasicos y un split correcto por compuesto, el modelo no generaliza. Ese resultado negativo (documentado aparte, no aqui) es evidencia empirica de que los descriptores tabulares no alcanzan con este volumen de datos, y motiva por que el proyecto JIC apuesta a representar la molecula como grafo en vez de como vector de descriptores.

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

Los ChEMBL IDs y familias quimicas de los 20 ingredientes estan curados en `config/chembl/mida_registry.json` y se cargan via `MidaRegistry` (lookup local, sin API).

Estos 20 ingredientes son el punto de partida, pero **no son el conteo final de compuestos del dataset**: la extraccion usa el corpus PubChem completo (~235 candidatos, ver seccion 6) porque cada ingrediente arrastra formas emparentadas (sales, isomeros, metabolitos, entradas duplicadas de PubChem que resuelven a distintos `chembl_id`). Del total de candidatos, solo una parte tiene bioactividad registrada en ChEMBL con `pchembl_value` calculable. El numero real de compuestos unicos que llegan con actividad util es ~107 (ver 8.bis).

---

## 3. Pipeline de extraccion

```
pubchem_panama_cids.csv (~235 CIDs de PubChem)
     |
     v  PASO 1: Carga corpus completo (SMILES validos)
chembl_corpus_compounds.csv (~235 compuestos)
     |
     v  PASO 2: Resolucion cascada PubChem -> ChEMBL ID
chembl_corpus_mapping.csv (~235 filas con match_method y match_status)
     |
     v  PASO 3: Descarga bioactividad por ChEMBL ID
     v  13 tipos de ensayo: IC50, EC50, Ki, Kd, Potency, Inhibition,
     v  AC50, LC50, GI50, MIC, LD50, ED50, IC90
     |
     v  PASO 4: Enriquecimiento con diana, ensayo, descriptores moleculares
chembl_panama_bioactivity_raw.csv (10,745 registros)
     |
     v  PASO 5: Filtros de calidad + derivacion activity_class
chembl_panama_bioactivity.csv (3,608 registros, ~107 compuestos unicos)
```

El pipeline tecnico corre sobre el corpus completo (235 candidatos, familias emparentadas incluidas), no solo sobre los 20 nombres MIDA literales; por eso la salida final tiene mas compuestos que ingredientes activos nominales, pero muchos menos que candidatos de entrada (la mayoria no tiene bioactividad registrada en ChEMBL).

---

## 4. Detalle de cada paso

### Paso 1 — Carga del corpus completo

**Clase:** `CorpusLoader.load()` en `acquisition/common.py`

```python
# Todos los compuestos PubChem con SMILES válido (~235)
compounds = CorpusLoader().load("data/raw/pubchem_panama_cids.csv")
```

Los 20 ingredientes MIDA se marcan con `is_mida=True` via `MidaRegistry`; su familia química se toma del registro JSON cuando aplica.

**Salida:** `data/raw/chembl_corpus_compounds.csv` (~235 filas)

| Columna | Tipo | Ejemplo |
|---|---|---|
| compound_name | str | Chlorpyrifos |
| pubchem_cid | int | 2730 |
| smiles | str | CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl |
| family | str | Organophosphates |
| source | str | MIDA_name_search |
| is_mida | bool | True |

### Paso 2 — Resolucion ChEMBL ID (cascada)

**Clase:** `ChemblIdResolver.resolve()` en `acquisition/local.py`

Estrategia de resolucion en 5 niveles:

| Nivel | Metodo | Fuente | Criterio |
|---|---|---|---|
| 0 | known_registry | `config/chembl/mida_registry.json` | Lookup en `MidaRegistry` |
| 1 | pubchem_xref | SQLite `compound_structures` + xref | CID de PubChem |
| 2 | smiles | SQLite | SMILES canonico RDKit |
| 3 | pref_name | SQLite `molecule_dictionary` | Nombre exacto |
| 4 | synonym | SQLite `molecule_synonyms` | Sinonimo registrado |

Todas las consultas corren contra `chembl_37.db` via SQLAlchemy Core (`acquisition/sqlalchemy.py`).

```sql
-- Ejemplo: match por SMILES
SELECT DISTINCT md.chembl_id
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE cs.canonical_smiles = ?
```

**Salida:** `data/raw/chembl_corpus_mapping.csv`

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

**Clase:** `ChemblDatabase.fetch_activities()` / `build_bioactivity_table()` en `acquisition/local.py`

Por cada `chembl_id` valido, ejecuta un `SELECT` con join de 7 tablas reflejadas (actividades, ensayos, dianas, propiedades moleculares) filtrado por los `standard_type` de `config/chembl/standard_types.json`.

**Campos descargados por registro:**

| Grupo | Campos |
|---|---|
| Actividad | activity_id, standard_type, standard_value, standard_units, standard_relation, pchembl_value, data_validity_comment, activity_comment |
| Diana | target_chembl_id, target_name, target_type, organism |
| Ensayo | assay_chembl_id, assay_type, bao_label |
| Molecula | mw_freebase, alogp, psa, hba, hbd, aromatic_rings, heavy_atoms, rtb, num_ro5_violations, cx_logp, cx_logd, molecular_species |

Cuatro de estos campos merecen mencion aparte porque **ya no son metadata de paso**, sino insumo directo de fases posteriores:

- `standard_relation` — indica si el valor es exacto (`=`) o censurado (`>`, `<`). Es la base de la honestidad estadistica en Fase 2 y Fase 4: un valor `IC50 > 10000 nM` no es lo mismo que `IC50 = 10000 nM`, y tratarlos igual infla o distorsiona agregados.
- `target_chembl_id` y `target_name` — identifican la diana biologica de cada ensayo. Se usan para medir promiscuidad (cuantas dianas distintas toca cada compuesto) y para el heatmap compuesto x diana de la Fase 3.
- `standard_type` — el tipo de ensayo (IC50, Ki, Potency, etc.). Se usa para contrastar potencia por tipo de endpoint en vez de mezclarlos sin mas.

### Paso 4 — Derivacion de activity_class

**Clase:** `ActivityClassAssigner.assign()` en `acquisition/common.py` (umbral desde `config/chembl/standard_types.json`)

| Clase | Criterio | Significado |
|---|---|---|
| Active | pchembl_value >= 6.0 | IC50 <= 1 uM (biologicamente activo) |
| Inactive | pchembl_value < 6.0 | IC50 > 1 uM |
| NaN | Sin pChEMBL | No evaluable |

**Importante — que es y que ya no es esta columna:** `activity_class` se sigue generando aqui porque es una columna derivada barata y util para describir el dataset (por ejemplo, "que fraccion de mediciones por familia caen del lado activo"). Pero **ya no es la variable objetivo de ningun modelo supervisado**. En el diseno original se uso como target de clasificacion; el intento fallo porque es circular respecto a `pchembl_value` (es literalmente su binarizacion) y porque a nivel de compuesto (la unidad de analisis correcta) 63 de 107 compuestos tienen ambas clases segun la diana evaluada — no hay una "clase" unica por compuesto. De aqui en adelante, `activity_class` se usa solo descriptivamente (conteos, proporciones), nunca como target.

**Imputacion de pChEMBL faltante:** `PchemblImputer.impute_dataframe()` calcula `pChEMBL = -log10(valor_en_molar)` cuando `standard_relation == '='` y el valor es convertible a molar. Factores de unidad en `config/chembl/concentration_units.json`.

```python
# ConcentrationUnits.molar_factor(units) — ver concentration_units.json
factor = ConcentrationUnits.molar_factor(units)  # nM -> 1e-9, uM -> 1e-6, etc.
molar = value * factor
pchembl = -math.log10(molar)
```

### Paso 5 — Filtros de calidad

**Clase:** `QualityFilterPipeline.apply()` en `acquisition/common.py` (config en `config.yaml` → `chembl.quality_filters`)

| Filtro | Accion | Registros tipicos eliminados |
|---|---|---|
| `pchembl_value` nulo y no imputable | Excluir | ~40% del raw |
| `data_validity_comment` presente | Excluir datos dudosos | ~5% |

**Cambio respecto al diseno original:** antes este paso excluia toda fila con `standard_relation != '='` (~15% del raw), es decir, tiraba los valores censurados (`>`, `<`). Ese filtro ya no aplica asi: las filas censuradas **se conservan** en el CSV limpio junto con su `standard_relation` original, para que la Fase 2 decida explicitamente como tratarlas (excluirlas de agregados de punto, marcarlas, o usarlas solo para conteos de cobertura) en vez de que desaparezcan sin dejar rastro en la Fase 1. `require_exact_relation` en `config.yaml` queda documentado como controla unicamente la imputacion de pChEMBL (paso 4), no el filtrado de filas.

El CSV raw se conserva intacto para auditoria. Solo el CSV limpio pasa a la Fase 2.

---

## 4.bis Notas de implementacion tecnica

### Backend unico: SQLite local

La extraccion usa **solo** `chembl_37.db` (ChEMBLdb SQLite). No hay cliente REST ni dependencia de `chembl_webresource_client`. Las consultas usan SQLAlchemy 2.0 Core con reflexion parcial de 7 tablas.

### Orquestador y constantes

```python
from src.analisis_proyecto.acquisition.extract import ChemblExtractor

extractor = ChemblExtractor.from_config_file("config/config.yaml")
result = extractor.run("data/raw/pubchem_panama_cids.csv")
# result.compounds, result.mapping, result.raw, result.clean, result.summary
```

Constantes editables en `config/chembl/` (MIDA, columnas, tipos de actividad, unidades, esquema SQLite).

### Clases principales (`src/analisis_proyecto/`)

| Clase / modulo | Rol |
|---|---|
| `ChemblExtractor` | Pipeline completo corpus → mapping → bioactividad → filtros |
| `ChemblDatabase` | Consultas SQLite (mapping, actividades, metadatos DB) |
| `ChemblIdResolver` | Mapeo en cascada PubChem → ChEMBL ID |
| `CorpusLoader` | Carga corpus PubChem completo (SMILES válidos) |
| `QualityFilterPipeline` | Filtros de calidad + stats de exclusion |
| `ActivityClassAssigner` | Active / Inactive (uso descriptivo) |
| `PchemblImputer` | Imputacion pChEMBL desde standard_value |
| `ExtractionSummarizer` | Resumen por compuesto |

### Verificacion rapida desde terminal

```bash
# Confirmar que la DB es legible
make test-chembl

# Extraccion completa
make chembl-extract

# Verificar resolucion de un compuesto (Python)
python -c "
from src.analisis_proyecto.acquisition.extract import ChemblExtractor
from src.analisis_proyecto.core.models import CorpusCompound
from src.analisis_proyecto.acquisition.local import ChemblIdResolver

extractor = ChemblExtractor.from_config_file('config/config.yaml')
compound = CorpusCompound('Chlorpyrifos', 2730, 'CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl', 'Organophosphates')
match = ChemblIdResolver().resolve(compound, extractor.database._sql, extractor.database._sql.schema())
print(match.to_dict())
"
```

---

## 5. Trabajo por rol

### Ingeniero de Datos (LIDER)

| # | Tarea | Archivo | Componente clave |
|---|---|---|---|
| 1 | Configurar extraccion | `config/config.yaml` + `config/chembl/*.json` | Seccion `chembl:` |
| 2 | Consultas ChEMBL | `acquisition/remote.py`, `acquisition/server.py`, `acquisition/local.py` | Cliente HTTP + servidor SQLite (Docker) |
| 3 | Orquestador | `acquisition/extract.py` | `ChemblExtractor.run()` |
| 4 | Mapeo cascada ChEMBL ID | `acquisition/local.py` | `ChemblIdResolver` |
| 5 | Filtros e imputacion | `acquisition/common.py` | `QualityFilterPipeline`, `PchemblImputer` |
| 6 | Script CLI | `scripts/fase1/extract_chembl.py` | `main()` |
| 7 | Verificacion DB | `scripts/fase1/verify_acquisition/db.py` | `make test-chembl` |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Verificar conexion al servidor | Ejecutar `make test-chembl` (health + consulta de prueba via HTTP) |
| Documentar esquema de salida | Verificar que columnas coincidan con lo esperado por Fase 2/3 (incluyendo `standard_relation`, `target_chembl_id`, `target_name`, `standard_type`) |
| Probar corpus completo | Verificar ~235 compuestos cargados y conteo `is_mida == 20` |

### Analista / Cientifico de Datos

No participan directamente en esta fase. Reciben `chembl_panama_bioactivity.csv` como entrada para construir, en Fase 2, las dos tablas de trabajo (`activities_clean.csv` a nivel medicion y `compounds_features.csv` a nivel compuesto).

---

## 6. Configuracion

### config/config.yaml (seccion chembl)

```yaml
chembl:
  version: "37"
  server_url: http://127.0.0.1:8765   # host → chembl-server (Docker)
  standard_types: expanded             # o lista explicita; ver standard_types.json
  pchembl_active_threshold: 6.0
  quality_filters:
    impute_pchembl: true
    require_exact_relation: true       # solo afecta imputacion (paso 4), no descarta filas
    exclude_validity_comment: true
```

## 7. Ejecucion

La BD ChEMBL (~30 GB) vive en el volumen Docker `jic2026_chembl_db`. El host la consulta via **chembl-server** (HTTP, puerto 8765) — igual que Postgres o MinIO.

```yaml
# config/config.yaml
chembl:
  server_url: http://127.0.0.1:8765
```

```bash
# 1. Descargar BD al volumen (una vez; reutiliza jic2026_chembl_db si ya existe)
make setup-chembl

# 2. Solo levantar el servidor (si la BD ya esta descargada)
make chembl-server-up

# 3. Verificar conexion
make test-chembl

# 4. Extraer CSVs
make chembl-extract

# 5. Notebook
jupyter notebook "proyecto analisis/notebooks/fase1_adquisicion.ipynb"
```

Health check manual: `curl http://127.0.0.1:8765/health`

---

## 8. Salidas y volumenes esperados

| Archivo | Filas | Columnas | Tamano |
|---|---|---|---|
| `chembl_corpus_compounds.csv` | ~235 | 6 | ~15 KB |
| `chembl_corpus_mapping.csv` | ~235 | 9 | ~25 KB |
| `chembl_panama_bioactivity_raw.csv` | ~10,745 | 33 | ~5 MB |
| `chembl_panama_bioactivity.csv` | ~3,608 | 33 | ~2 MB |

`chembl_panama_bioactivity.csv` tiene 3,608 filas pero solo **~107 valores unicos de `chembl_id`/`compound_name`/`smiles`** — es decir, 3,608 mediciones repartidas sobre 107 moleculas (media de ~34 mediciones por compuesto). `standard_relation`, `target_chembl_id`, `target_name` y `standard_type` estan entre las 33 columnas y llegan intactas hasta este CSV; no se pierden en el camino.

### 8.bis Por que 107 compuestos no alcanza para un modelo predictivo

Este es el numero que mas condiciona el diseno de las fases siguientes, asi que vale dejarlo explicito aca, en el origen del dato:

- Los 20 ingredientes activos del MIDA, mas sus formas emparentadas y familias relacionadas del corpus completo, resuelven a **~107 compuestos unicos** con bioactividad registrada en ChEMBL.
- Los 8 descriptores moleculares precalculados (mw_freebase, alogp, psa, hba, hbd, aromatic_rings, rtb, heavy_atoms) son **constantes dentro de cada compuesto**: no varian entre las distintas mediciones de una misma molecula. Esto significa que, para cualquier tarea que use esos descriptores como entrada, el modelo en realidad solo "ve" 107 vectores de entrada distintos — el resto de las 3,608 filas son repeticiones del mismo vector con distinto resultado de bioactividad.
- 107 puntos de entrada es un dataset **chico para machine learning supervisado**, sobre todo si se pretende evaluar generalizacion con un split honesto (por compuesto, no por fila). Splitear por fila deja moleculas identicas en train y test y produce metricas artificialmente altas; splitear por compuesto es lo correcto, pero con solo ~75-85 compuestos de entrenamiento el modelo no tiene con que generalizar.
- Por esta razon el proyecto se reencuadra como **descriptivo y multivariado**: caracterizar, agrupar y contrastar los 107 compuestos (Fases 3 y 4), en vez de forzar una prediccion que el volumen de datos no puede sostener. El intento predictivo original se documenta como **resultado negativo honesto** en la [Fase 4 — §12 Baseline predictivo (P6)](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6), que funciona como puente hacia el proyecto JIC: motiva por que ese proyecto usa grafos moleculares (GNN-GIN) entrenados sobre Tox21 (~8,000 compuestos) en vez de descriptores tabulares sobre un corpus de 107.

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
- [ ] ~107 compuestos unicos documentados como conteo final (no solo las 3,608 filas)
- [ ] Todas las columnas documentadas presentes en el CSV final, incluyendo `standard_relation`, `target_chembl_id`, `target_name` y `standard_type` (trazabilidad para Fase 2/3/4)
- [ ] Ninguna fila se descarta por `standard_relation != '='`; la censura (`>`, `<`) queda registrada, no eliminada
- [ ] CSV raw conservado para auditoria
- [ ] Porcentaje de pChEMBL imputado documentado (y limitado a mediciones con relacion exacta)
- [ ] El limite de tamano (n=107 compuestos) para fines predictivos queda explicitado en la documentacion de esta fase, no descubierto recien en Fase 4
- [ ] `make test-chembl` pasa sin errores

---

## 11. Diagrama de dependencias

```
config/config.yaml
config/chembl/*.json
     |
     v
src/analisis_proyecto/acquisition/extract.py  (ChemblExtractor)
     |
     +---> acquisition/common.py   (CorpusLoader, filtros, imputacion)
     |
     +---> acquisition/remote.py   (ChemblRemoteDatabase — cliente HTTP)
     |         |
     |         v
     |     chembl-server :8765  (Docker, volumen jic2026_chembl_db)
     |         |
     |         +---> acquisition/local.py + acquisition/sqlalchemy.py
     |
     v
data/raw/chembl_panama_bioactivity.csv
```

---

*Siguiente fase:* [Fase 2 — Limpieza e ingenieria de datos](fase2_limpieza_datos.md)
