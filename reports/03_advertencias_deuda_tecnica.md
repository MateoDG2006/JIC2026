# Advertencias y Deuda Técnica — Segunda Pasada

> Las advertencias WARN-1 a WARN-8 de la primera pasada están corregidas. Este reporte documenta las nuevas advertencias encontradas en el código corregido.

---

## WARN-9 — `pubchem_api.py:107`: `.map()` descarta silenciosamente resultados "Inconclusive", "Probe" y "Unspecified"

**Archivo:** `src/data/pubchem_api.py:107–111`  
**Severidad:** Advertencia de datos — pérdida silenciosa de registros del bioensayo

### Descripción

`fetch_bioassay_data()` mapea el campo `PUBCHEM_ACTIVITY_OUTCOME` a 0/1 y luego hace `.dropna()`:

```python
df["activity"] = df["activity_raw"].map({"Active": 1, "Inactive": 0})
...
return df[["CID", "task", "AID", "activity"]].dropna()
```

Los ensayos PubChem Tox21 incluyen al menos cuatro categorías de outcome:

| Valor en PubChem | Frecuencia típica | Resultado del `.map()` |
|---|---|---|
| `"Active"` | ~5–15% | 1 |
| `"Inactive"` | ~60–80% | 0 |
| `"Inconclusive"` | ~5–20% | **NaN → descartado** |
| `"Probe"` | raro | **NaN → descartado** |

Los registros "Inconclusive" no son ruido — son moléculas con actividad ambigua que sí tienen SMILES válidos. Descartarlos silenciosamente reduce el tamaño del dataset y puede sesgar la distribución de negativos.

### Corrección recomendada

Registrar cuántos registros no son Active/Inactive antes de descartarlos:

```python
n_before = len(df)
df["activity"] = df["activity_raw"].map({"Active": 1, "Inactive": 0})
n_dropped = df["activity"].isna().sum()
if n_dropped > 0:
    print(f"[INFO] AID {aid} ({task_name}): {n_dropped}/{n_before} registros descartados "
          f"(outcomes: {df.loc[df['activity'].isna(), 'activity_raw'].value_counts().to_dict()})")
return df[["CID", "task", "AID", "activity"]].dropna()
```

---

## WARN-10 — `featurizer.py:13`: `HybridizationType.S` incluido innecesariamente en la lista de hibridaciones

**Archivo:** `src/data/featurizer.py:13`  
**Severidad:** Advertencia leve — dimensión de feature siempre cero para agroquímicos

### Descripción

La lista `HYBRIDIZATION` incluye `HybridizationType.S`:

```python
HYBRIDIZATION: list[Chem.rdchem.HybridizationType] = [
    Chem.rdchem.HybridizationType.S,      # ← orbital S puro: solo noble gases / hidrógeno desnudo
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]
```

`HybridizationType.S` corresponde a hibridación de orbital s puro, que RDKit asigna a átomos de gases nobles y algunos metales en estado de oxidación inusual. Ningún agroquímico orgánico (organofosforados, triazinas, piretroides, fungicidas azólicos) contiene este tipo de hibridación.

El resultado es que la primera posición del one-hot de hibridación (6 posiciones) **siempre es 0** para todo el corpus panameño. Esto no rompe el modelo, pero desperdicia una dimensión del vector de features nodales y puede confundir futuros desarrolladores que asuman que todas las posiciones del one-hot son informativas.

### Corrección recomendada

Eliminar `HybridizationType.S` de la lista:

```python
HYBRIDIZATION: list[Chem.rdchem.HybridizationType] = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
    # "other" está implícito en el catch-all de _one_hot_value
]
```

**Nota:** Cambiar esto modifica `NODE_FEAT_DIM` de 45 a 44. Actualizar el assert en `featurizer.py:91` y el parámetro `in_channels` en `GINToxicity`.

---

## WARN-11 — `CLAUDE.md:1108–1111`: código de referencia de `run_5fold_cv` tiene dos errores de API

**Archivo:** `CLAUDE.md:1108, 1111`  
**Severidad:** Advertencia de documentación — cualquier desarrollador que copie el snippet obtendrá errores inmediatos

### Descripción

El bloque de ejemplo en `CLAUDE.md` para la función `run_5fold_cv` tiene dos inconsistencias con la API real:

**Error 1 — llamada con argumentos incorrectos (línea 1108):**

```python
# CLAUDE.md — INCORRECTO
folds = create_scaffold_folds(smiles_list, n_folds=5)
```

La firma actual de `create_scaffold_folds` requiere `smiles_list` y `train_val_idx` como argumentos posicionales. La llamada del ejemplo omite `train_val_idx`, lo que produce `TypeError` al ejecutarse.

**Error 2 — desempaquetado de 3-tupla cuando la función retorna 2-tuplas (línea 1111):**

```python
# CLAUDE.md — INCORRECTO
for fold_idx, (train_idx, val_idx, test_idx) in enumerate(folds):
```

`create_scaffold_folds()` retorna `list[tuple[list[int], list[int]]]` — solo `(train_idx, val_idx)`. El conjunto de test se fija externamente antes de llamar a esta función (ver `AGENTS.md`). Este desempaquetado produce `ValueError: not enough values to unpack`.

### Corrección recomendada

Actualizar el bloque de `CLAUDE.md:1103–1126`:

```python
def run_5fold_cv(smiles_list, labels_array, mask_array, model_config, train_config):
    test_idx  = train_config["test_idx"]   # fijo para todo el experimento
    tv_idx    = [i for i in range(len(smiles_list)) if i not in set(test_idx)]
    folds     = create_scaffold_folds(smiles_list, tv_idx, n_folds=5, seed=42)
    results   = []

    for fold_idx, (train_idx, val_idx) in enumerate(folds):
        ...
```
