# Errores Críticos — Segunda Pasada

> Los errores C-1 a C-4 de la primera pasada están corregidos. Este reporte documenta los nuevos errores críticos introducidos o descubiertos en el código corregido.

---

## ERROR NC-1 — `prepare_tox21_graphs.py`: índices del JSON no corresponden a posiciones en los `.pt`

**Archivo:** `scripts/prepare_tox21_graphs.py:112–130`  
**Severidad:** Crítico — corrupción silenciosa de datos al usar los índices guardados

### Descripción

`save_split_indices()` guarda los índices como rangos contiguos basados en el tamaño de los `DiskDataset` de DeepChem:

```python
n_train = len(train_ds)          # p.ej. 6265
n_val   = len(val_ds)            # p.ej. 783
n_test  = len(test_ds)           # p.ej. 784

train_idx = list(range(0, n_train))
val_idx   = list(range(n_train, n_train + n_val))
test_idx  = list(range(n_train + n_val, n_train + n_val + n_test))
```

Sin embargo, `_build_list()` descarta cualquier molécula cuyo `smiles_to_graph()` retorne `None`. Los archivos `graphs_{train,val,test}.pt` contienen **solo las moléculas filtradas**, por lo que su longitud puede ser menor que `n_train / n_val / n_test`. El propio campo `meta` del JSON lo reconoce explícitamente:

> `"no coinciden con filas omitidas al fallar SMILES→grafo"`

Si alguien carga `scaffold_split_indices.json` y usa esos índices para acceder a las listas de grafos de los `.pt`, obtendrá moléculas incorrectas o un `IndexError`.

### Impacto

Cualquier código que cargue los índices del JSON y los use para indexar dentro de los `.pt` introduce sesgo de selección o errores de runtime. La CV posterior queda inválida.

### Corrección recomendada

Guardar los índices **después** del filtrado, numerando los grafos que sí pasaron la featurización:

```python
# En _build_list(), retornar también los índices de origen que sobrevivieron
def _build_list(smiles, y, mask):
    out, kept = [], []
    for i, smi in enumerate(smiles):
        g = smiles_to_graph(smi, labels=y[i].tolist(), mask=mask[i].tolist())
        if g is not None:
            out.append(g)
            kept.append(i)
    return out, kept
```

Alternativamente, guardar el índice original de DeepChem como atributo en cada objeto `Data` (`g.orig_idx = i`) para poder reconstruir la correspondencia.

---

## ERROR NC-2 — `cross_validation.py`: cambio de API sin retrocompatibilidad + código de referencia incorrecto en `CLAUDE.md`

**Archivos:** `src/evaluation/cross_validation.py:45`, `CLAUDE.md:1108`  
**Severidad:** Crítico — silencia errores o produce resultados incorrectos en producción

### Descripción

La corrección de ML-2 añadió `smiles_list` como primer parámetro de `create_scaffold_folds()`, convirtiendo la firma de:

```python
# Firma ANTERIOR
def create_scaffold_folds(train_val_idx, n_folds=5):
```

en:

```python
# Firma ACTUAL
def create_scaffold_folds(smiles_list, train_val_idx, n_folds=5, seed=42):
```

**Problema 1:** El código de referencia en `CLAUDE.md:1108` usa la llamada errónea:

```python
folds = create_scaffold_folds(smiles_list, n_folds=5)
# Falta train_val_idx → TypeError al ejecutarse
```

**Problema 2:** El mismo bloque en `CLAUDE.md:1111` desempaqueta los folds como 3-tuplas:

```python
for fold_idx, (train_idx, val_idx, test_idx) in enumerate(folds):
```

Pero la función retorna 2-tuplas `(train_idx, val_idx)`. Esto produce `ValueError: not enough values to unpack` en runtime.

### Impacto

Cualquier desarrollador que copie el ejemplo de `CLAUDE.md` directamente obtendrá errores inmediatos. Si alguna versión del código de entrenamiento usa la firma antigua, el parámetro `smiles_list` recibirá una lista de enteros, lo que hace que `_murcko_scaffold()` sea llamado con un entero en lugar de un string SMILES, produciendo un `TypeError` difícil de rastrear.

### Corrección recomendada

Actualizar `CLAUDE.md:1108` y `CLAUDE.md:1111`:

```python
# Correcto — CLAUDE.md:1108
all_idx = list(range(len(smiles_list)))
train_val_idx = [i for i in all_idx if i not in set(test_idx)]
folds = create_scaffold_folds(smiles_list, train_val_idx, n_folds=5, seed=42)

# Correcto — CLAUDE.md:1111
for fold_idx, (train_idx, val_idx) in enumerate(folds):
    ...
```

---

## ERROR NC-3 — `trainer.py:109`: NaN consume el contador de paciencia y puede terminar el entrenamiento sin guardar ningún checkpoint

**Archivo:** `src/training/trainer.py:99–112`  
**Severidad:** Crítico — puede causar que el entrenamiento termine con `best=0.0` y sin modelo en disco

### Descripción

La corrección de C-2 añadió un guard para `val_auc = NaN`, pero la rama NaN incrementa `bad` antes de hacer `continue`:

```python
if not np.isfinite(val_auc):
    ...
    bad += 1          # ← consume paciencia aunque el modelo no haya tenido oportunidad de mejorar
    if bad >= patience:
        break
    continue
```

En Tox21 es frecuente que las primeras épocas produzcan `val_auc = NaN` porque, con batches pequeños y clases desbalanceadas, el conjunto de validación puede tener solo una clase para las 12 tareas simultáneamente (condición que `evaluate_multitask_auc` maneja retornando `NaN`). Si esto ocurre durante `patience` épocas consecutivas al inicio, el loop termina con:

- `best = 0.0` (valor inicial, nunca actualizado)
- ningún checkpoint en disco (`save_path` nunca se escribe)
- `train()` retorna `0.0` sin error visible

El código que llame a `torch.load(save_path)` después lanzará `FileNotFoundError`.

### Escenario real

Con `early_stopping_patience = 50` y un modelo que produce NaN durante las primeras 50 épocas (posible con learning rate alto sin warm-up o con val set muy pequeño), el entrenamiento completo se descarta silenciosamente.

### Corrección recomendada

Separar el contador de NaN del contador de "sin mejora", o no acumular `bad` durante rachas de NaN:

```python
nan_streak = 0
MAX_NAN_STREAK = 10  # abortar solo si NaN persiste mucho tiempo

if not np.isfinite(val_auc):
    nan_streak += 1
    if nan_streak >= MAX_NAN_STREAK:
        break
    continue

nan_streak = 0  # reset al recuperarse
# sched.step, comparar con best, etc.
```
