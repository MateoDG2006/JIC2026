# Errores de ML — Segunda Pasada

> Los errores ML-1 a ML-4 de la primera pasada están corregidos. Este reporte documenta los nuevos errores de ML descubiertos en el código corregido.

---

## ERROR NML-1 — `chemical_coherence.py`: patrones SMARTS demasiado genéricos inflan artificialmente Precision@k

**Archivo:** `src/evaluation/chemical_coherence.py:15–19`  
**Severidad:** Error de ML — la métrica de coherencia química no mide lo que pretende medir

### Descripción

Tres patrones en `TOXIC_GROUPS` son tan genéricos que coinciden con la gran mayoría de los agroquímicos, haciendo que Precision@k sea cercana a 1.0 para esas tareas independientemente de la calidad de la explicación XAI:

| Tarea | Patrón problemático | Problema |
|---|---|---|
| `NR-PPAR-gamma` | `"CCCC"` | Coincide con cualquier cadena de 4 carbonos alifáticos consecutivos — presente en casi todos los pesticidas |
| `NR-AhR` | `"c1ccccc1"` | Coincide con cualquier anillo bencénico — presente en la mayoría de los organofosforados, piretroides y fungicidas azólicos |
| `NR-PPAR-gamma` | `"c1ccccc1"` | Mismo patrón ultra-genérico, duplicado en otra tarea |

```python
# chemical_coherence.py:15–19
"NR-AhR":       ["c1ccccc1", "c1ccncc1", "c1ccoc1"],      # c1ccccc1 ≈ cualquier aromático
"NR-PPAR-gamma": ["C(=O)O", "c1ccccc1", "CCCC"],          # c1ccccc1 + CCCC ≈ match trivial
```

### Impacto

Precision@k reportará valores altos para `NR-AhR` y `NR-PPAR-gamma` sin que la explicación sea útil. Si se usa esta métrica para comparar GNNExplainer vs. Grad-CAM, los resultados serán engañosos: cualquier método que señale cualquier átomo dentro de un anillo bencénico o una cadena alifática "ganará" automáticamente.

### Corrección recomendada

Reemplazar por patrones más específicos para los receptores nucleares implicados:

```python
# NR-AhR: receptor de hidrocarburo arílico — responde a HAPs, dioxinas, bifenilos policlorados
"NR-AhR": [
    "c1ccc2ccccc2c1",    # naftaleno (HAP bicíclico)
    "c1ccc(-c2ccccc2)cc1",  # bifenilo
    "c1ccoc1",           # furano
    "c1ccncc1",          # piridina
],

# NR-PPAR-gamma: receptor activado por proliferador de peroxisomas gamma
"NR-PPAR-gamma": [
    "C(=O)O",            # ácido carboxílico / éster
    "c1ccc(OCC(=O))cc1", # tiazolidinediona / fibrato — cabeza de ácido ariltioxiacético
    "n1ccnc1",           # imidazol
],
```

---

## ERROR NML-2 — `grad_cam.py:35`: `task_index` no tiene validación de rango; produce `IndexError` silencioso

**Archivo:** `src/xai/grad_cam.py:33–35`  
**Severidad:** Error de ML — crash no informativo en producción; sin validación de precondición

### Descripción

La función `grad_cam_graph()` recibe `task_index: int` y lo usa directamente para indexar el tensor de salida del modelo:

```python
logits = model(data.x, data.edge_index, batch)  # shape: (1, 12)
logits[0, task_index].backward()                # IndexError si task_index < 0 o >= 12
```

No hay ninguna comprobación de que `task_index` esté en `[0, n_tasks)`. Si el modelo tiene 12 salidas y se llama con `task_index=12` o `task_index=-1`:

- `task_index = 12` → `IndexError: index 12 is out of bounds for dimension 1 with size 12`
- `task_index = -1` → Python interpreta el índice negativo como la última tarea (tarea 11), lo que es un comportamiento incorrecto silencioso — el usuario cree que explica la tarea 11 (`SR-p53`) pero en realidad puede estar explicando otra

### Impacto

En el pipeline de aplicación panameña donde se itera sobre las 12 tareas con un índice externo, un off-by-one en el bucle produciría bien un crash, bien una explicación silenciosamente incorrecta.

### Corrección recomendada

Añadir validación explícita antes del backward pass:

```python
n_tasks = logits.shape[1]
if not (0 <= task_index < n_tasks):
    raise ValueError(
        f"task_index={task_index} fuera de rango [0, {n_tasks}). "
        f"Usa un índice de 0 a {n_tasks - 1}."
    )
logits[0, task_index].backward()
```
