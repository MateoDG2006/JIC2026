# Resumen de Auditoría de Código — Segunda Pasada

> **Estado primera pasada:** las correcciones de los reportes `01`–`03` originales (C-1 a C-4, ML-1 a ML-4, WARN-1 a WARN-8) están aplicadas en el código fuente actual del repositorio.
>
> **Esta pasada** analiza el código ya corregido y documenta los nuevos errores introducidos o previamente no detectados.

**Proyecto:** GNN-GIN + XAI para toxicidad de agroquímicos panameños  
**Archivos re-analizados:** 20 módulos Python + 1 script + 3 tests

---

## Distribución de errores (segunda pasada)

| Categoría | Cantidad | Archivo de detalle |
|---|---|---|
| Errores críticos (crash / datos corruptos) | 3 | `01_errores_criticos.md` |
| Errores de ML (métricas incorrectas o infladas) | 2 | `02_errores_ml.md` |
| Advertencias y deuda técnica | 3 | `03_advertencias_deuda_tecnica.md` |
| **Total** | **8** | |

---

## Mapa de archivos afectados

```
src/
├── training/
│   └── trainer.py          → NC-3  (NaN consume paciencia antes de que el modelo converja)
├── evaluation/
│   └── chemical_coherence.py→ NML-1 (SMARTS "CCCC" y "c1ccccc1" son trivialmente genéricos)
└── xai/
    └── grad_cam.py         → NML-2 (task_index sin validación de rango)

src/data/
├── featurizer.py           → WARN-10 (HybridizationType.S innecesario — siempre 0)
└── pubchem_api.py          → WARN-9  (outcomes "Inconclusive" descartados sin log)

scripts/
└── prepare_tox21_graphs.py → NC-1   (índices del JSON no coinciden con posiciones en .pt)

CLAUDE.md                   → NC-2, WARN-11 (create_scaffold_folds llamada con args incorrectos)
src/evaluation/
└── cross_validation.py     → NC-2   (API breaking change, CLAUDE.md aún usa firma vieja)
```

---

## Prioridad de corrección recomendada

### Antes de cualquier ejecución de entrenamiento

1. **NC-3** — `trainer.py:109` → separar contador NaN del contador de "sin mejora"
2. **NC-1** — `prepare_tox21_graphs.py` → guardar índices de las moléculas que sobrevivieron la featurización, no los del dataset original de DeepChem

### Antes de reportar métricas XAI

3. **NML-1** — `chemical_coherence.py:15,19` → reemplazar `"CCCC"` y `"c1ccccc1"` genéricos por SMARTS específicos para cada receptor nuclear
4. **NML-2** — `grad_cam.py:35` → añadir validación `0 <= task_index < n_tasks` antes del `.backward()`

### Antes de que otro desarrollador use el código

5. **NC-2** — `CLAUDE.md:1108,1111` → corregir llamada a `create_scaffold_folds()` en el ejemplo de `run_5fold_cv`

### Mejoras de robustez (baja urgencia)

6. **WARN-9**  — `pubchem_api.py:107` → loguear los outcomes descartados por `.dropna()`
7. **WARN-10** — `featurizer.py:13` → eliminar `HybridizationType.S` (actualizar `NODE_FEAT_DIM`)
8. **WARN-11** — `CLAUDE.md:1111` → corregir desempaquetado de 2-tupla en el ejemplo del bucle de CV
