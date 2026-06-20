# Auditoría del Proyecto JIC2026 — Reporte Completo

**Fecha:** 2026-06-20
**Alcance:** Requisitos de analítica, coherencia de datos, arquitectura del dashboard

---

## 1. Cumplimiento de Requisitos del Proyecto de Analítica de Datos

### 1.1 Checklist de Requisitos del Curso

| Requisito | Estado | Ubicación | Observaciones |
|---|---|---|---|
| Estadísticas descriptivas (media, mediana, moda, desv. std) | OK | Notebook 01, Sección 1 | Implementado en `chembl_preprocessing.summary_statistics()` |
| Distribuciones (histogramas, boxplots) | OK | Notebook 01, Sección 1 + Dashboard Tab Exploración | Histogramas por variable, boxplots por familia |
| Visualización datos faltantes (missingno) | OK | Notebook 01, Sección 2 | Matrix, bar y heatmap generados |
| UpSetPlot de patrones NaN | OK | Notebook 01, Sección 2 | Usa `from_indicators` correctamente |
| Imputación (regla >250 NaN) | OK | Notebook 01, Sección 2 | Mediana por familia + fallback global |
| Correlación (2+ métodos) | OK | Notebook 01, Sección 3 | Pearson + Spearman implementados |
| Clasificación (2+ algoritmos) | OK | Notebook 01, Sección 4 | Random Forest + SVM (RBF kernel) |
| Accuracy + Matriz de confusión | OK | Notebook 01, Sección 4 + Dashboard | CM y ROC en `model_eval.json` |
| Regresión (2+ algoritmos) | OK | Notebook 01, Sección 5 | SVR + Random Forest Regressor |
| Métricas R² train/test | OK | Notebook 01, Sección 5 | `metrics_summary.csv` con splits por filas y por compuesto |
| Dashboard Dash-Plotly | OK | `viz/` (FastAPI + Plotly.js) | Migrado desde Dash; ver sección 7 |
| >= 4 gráficos | OK | 4 tabs con 8+ gráficos | Histograma, boxplot, heatmap, scatter, CM, ROC, choropleth, bar |
| >= 2 controles interactivos | OK | Dropdowns, sliders, text inputs | 6+ controles en total |
| Predictor interactivo | OK | Tab "Modelos" | RF Regressor para pChEMBL con 9 inputs |
| Mapa interactivo | OK | Tab "Mapa Panamá" | Choropleth Mapbox con 76 distritos |
| Despliegue web | OK | `render.yaml` configurado | Gunicorn + Render ready |
| Artículo IEEE (max 7 pág.) | BORRADOR | `docs/articulo_ieee/borrador.md` | Expandir según plantilla IEEE |
| Video explicativo (max 7 min.) | GUION | `docs/video/guion.md` | Grabar según guion |

### 1.2 Resumen de Cumplimiento

- **Requisitos técnicos completados:** 17/17 (implementación)
- **Pendientes de entrega:** grabar video + formatear artículo IEEE final
- **Calidad general:** Alta — la implementación excede los requisitos mínimos

---

## 2. Coherencia y Calidad de los Datos

### 2.1 Problemas Encontrados en los Datos

#### CRITICO: Rendimiento GIN no supera objetivo del CLAUDE.md

| Modelo | AUC-ROC Promedio | Objetivo CLAUDE.md | Delta |
|---|---|---|---|
| Random Forest (baseline) | 0.7433 | >= 0.76 | **-0.017** |
| MLP (baseline) | 0.7071 | >= 0.78 | **-0.073** |
| SMILES2vec (baseline) | 0.7268 | >= 0.80 | **-0.073** |
| **GIN** | **0.7498** | **>= 0.82** | **-0.070** |

**Impacto:** Ningún modelo alcanza los objetivos de AUC definidos en CLAUDE.md. El GIN apenas supera al RF por +0.006 AUC, cuando el objetivo era superar por +0.05. Esto contradice la hipótesis de investigación.

**Tareas con AUC bajo en GIN:**
- NR-ER: 0.653 (muy bajo)
- SR-ARE: 0.693
- NR-ER-LBD: 0.715
- NR-Aromatase: 0.736
- SR-p53: 0.740

#### CRITICO: Regresión por compuesto con R² negativo

En `metrics_summary.csv`:

| Modelo | Split | Feature Set | R² Test |
|---|---|---|---|
| SVR_RBF | compuesto | descriptores | **-1.025** |
| RandomForest | compuesto | descriptores | **0.032** |
| SVR_RBF | compuesto | descriptores+ensayo | **-0.244** |
| RandomForest | compuesto | descriptores+ensayo | **0.169** |

**Impacto:** R² negativo indica que el modelo predice peor que la media. El split por compuesto (que es el evaluador honesto de generalización) muestra que los modelos de regresión **no generalizan** a compuestos no vistos.

#### CRITICO: Clasificación por compuesto con accuracy de 37.9%

| Modelo | Split | Accuracy Test |
|---|---|---|
| RandomForest | filas | 0.758 |
| RandomForest | compuesto | **0.379** |

**Impacto:** La diferencia de 38 puntos porcentuales entre split por filas (0.758) y por compuesto (0.379) evidencia **data leakage masivo** en el split por filas. El mismo compuesto aparece en train y test con descriptores moleculares idénticos, inflando métricas artificialmente.

#### MODERADO: Correlación MW-heavy_atoms = 0.99

La correlación de Pearson entre `mw_freebase` y `heavy_atoms` es 0.9909. Esto es colinealidad casi perfecta — una de las dos variables es redundante para modelado.

#### MODERADO: Datos INEC son estimaciones, no datos oficiales

El archivo `inec_sociodemografico.csv` tiene `fuente: estimacion_geografica_inec_mapi` para todos los registros. Los datos de población, superficie agrícola e índice de pobreza son **estimaciones generadas programáticamente**, no datos descargados del INEC real.

#### MENOR: Features cx_logp y cx_logd 100% NaN

Los features `cx_logp` y `cx_logd` están definidos en `FEATURE_COLS` de `chembl_preprocessing.py` pero tienen 100% NaN en los datos y se eliminan durante el preprocesamiento. Esto es inconsistente.

#### MENOR: `pchembl_imputed` sin documentar proporción

La columna `pchembl_imputed` indica qué valores fueron imputados desde `standard_value`, pero no hay documentación clara de qué porcentaje del dataset usa valores imputados vs. valores originales de ChEMBL.

### 2.2 Validación de Coherencia entre Archivos

| Verificación | Resultado | Detalle |
|---|---|---|
| Corpus PubChem (235) -> ChEMBL mapping (235) | OK | Mismo conteo |
| ChEMBL raw (10,745) -> clean (3,608) | OK | Reducción por filtros de calidad (66% eliminado) |
| GIN train+val+test (6,258+782+783=7,823) | OK | Consistente con Tox21 total |
| 12 tareas Tox21 en GIN y dashboard | OK | Mismo `TASK_NAMES` importado |
| Panama predictions (235) matches corpus | OK | Mismo conteo de compuestos |
| Modelos pkl (4 archivos) | OK | rf_classifier, rf_regressor, svm_classifier, svr_regressor |
| XAI SVGs (98 archivos) | OK | Indexados en `xai_index.json` |

### 2.3 Calidad del Análisis Estadístico

| Aspecto | Evaluación | Comentario |
|---|---|---|
| EDA descriptivo | Bueno | Media, mediana, moda, std por variable |
| Tratamiento de missing | Bueno | missingno + UpSetPlot + imputación por familia |
| Correlación | Bueno | Pearson + Spearman con suficientes variables |
| Split de evaluación | Parcial | Split por filas inflado; split por compuesto implementado pero muestra colapso |
| Clasificación | Aceptable | RF AUC 0.82 (por filas); 0.38 accuracy (por compuesto) |
| Regresión | Problemático | R² negativo en split honesto |
| Validación cruzada GIN | Ausente | Solo 1 fold ejecutado, no 5-fold CV |

---

## 3. Dashboard: Arquitectura y Tiempo Real

### 3.1 Arquitectura Actual (post-auditoría)

```
viz/
  app.py              ─── FastAPI unificado (GNN 3D + analytics)
  routes/analytics.py ─── EDA, modelos, toxicidad, mapa, comparativa
  services/dashboard/ ─── Artefactos + cache checksum + inferencia sklearn
  templates/          ─── HTML + Plotly.js CDN
  static/js/          ─── analytics_*.js
```

Legacy: `dashboard/README.md` (Dash eliminado).

### 3.2 Integración con el Proyecto JIC

| Componente JIC | Integrado en Dashboard | Cómo |
|---|---|---|
| GIN (Fase III) | SI | Predicciones precomputadas en `panama_pesticides_profile.csv` |
| XAI (Fase IV) | SI | 98 SVGs servidos vía `/xai/<filename>` |
| Baselines (Fase II) | SI | Pestaña `/panama/models` + `model_comparison.json` |
| Corpus Panamá (Fase I) | SI | ChEMBL clean + toxicity profile |
| Geodata (Flujo D) | SI | GeoJSON de 76 distritos |
| FastAPI 3D viewer | INTEGRADO | Misma app en `:8000` |

### 3.3 Actualización de datos — RESUELTO (P3)

Cache con invalidación por checksum MD5 (`viz/services/dashboard/cache.py`) + `POST /api/analytics/refresh`. Ya no se usa `@lru_cache` permanente en loaders principales.

### 3.4 Compatibilidad con Arquitectura JIC

| Aspecto | Estado | Problema |
|---|---|---|
| Misma base de código | OK | Analytics bajo `viz/` en el mismo repo |
| Rutas compartidas | OK | `config.py` resuelve desde `PROJECT_ROOT` |
| Dependencia circular | RESUELTO | `TASK_NAMES` local en `viz/config.py` (P5) |
| Deployment separado | OK | `render.yaml` + bundle mode |
| Config unificada | OK | Lee de `config/config.yaml` |

---

## 4. Inventario Completo de Errores y Fallas

### Errores Críticos

| # | Error | Archivo | Impacto |
|---|---|---|---|
| E1 | GIN AUC (0.75) no alcanza objetivo (0.82) | `outputs/results/gin_results.csv` | Hipótesis de investigación no validada |
| E2 | Solo 1 fold ejecutado, no 5-fold CV | `scripts/fase3/run_gin_cv.py` | Script + `make train-gin-cv`; ejecutar para resultados |
| E3 | Regresión R² negativo en split por compuesto | `metrics_summary.csv` | Modelo no generaliza |
| E4 | Clasificación accuracy 37.9% en split honesto | `metrics_summary.csv` | Data leakage evidente |
| E5 | Artículo IEEE no iniciado | `docs/articulo_ieee/borrador.md` | Borrador listo — formatear IEEE |
| E6 | Video explicativo no iniciado | `docs/video/guion.md` | Guion listo — grabar |

### Errores Moderados

| # | Error | Archivo | Impacto |
|---|---|---|---|
| M1 | Dashboard sin actualización en tiempo real | `viz/services/dashboard/cache.py` | RESUELTO — checksum + `/api/analytics/refresh` |
| M2 | Datos INEC son estimaciones sintéticas | mapa + API geo | MITIGADO — disclaimer en UI y `_meta.disclaimer` |
| M3 | Colinealidad MW/heavy_atoms no tratada | `chembl_preprocessing.py` | RESUELTO — `heavy_atoms` excluido de FEATURE_COLS |
| M4 | Import `src.data.dataset` en dashboard | `viz/config.py` | RESUELTO — TASK_NAMES local |
| M5 | Discrepancia métricas dashboard vs CSV | `model_eval.json` | MITIGADO — split compuesto en JSON + docs METRICAS |
| M6 | `FEATURE_COLS` incluye cx_logp/cx_logd eliminados | `chembl_preprocessing.py` | RESUELTO |

### Errores Menores

| # | Error | Archivo | Impacto |
|---|---|---|---|
| m1 | Baselines RF AUC (0.74) bajo objetivo (0.76) | `baseline_results.csv` | Señal de posible bug en pipeline de datos |
| m2 | Bundle GeoJSON nombre inconsistente | `prepare_dashboard.py` | RESUELTO — copia como `panama_distritos.geojson` |
| m3 | `potential_duplicate` flag sin acción | `filter_potential_duplicates()` | RESUELTO — eliminados en pipeline |
| m4 | Predictor usa 9 features, modelo entrenado con 9-42 | UI + `PREDICTOR_NOTE` | DOCUMENTADO — 8 descriptores + defaults ensayo |

---

## 5. Propuestas de Mejora

### 5.1 Prioridad ALTA — Corregir antes de presentar

#### P1: Mejorar rendimiento del GIN (E1, E2)

**Problema:** AUC 0.75 vs objetivo 0.82.

**Acciones:**
1. Ejecutar 5-fold CV completo (actualmente solo 1 fold)
2. Probar hiperparámetros: `hidden_dim=256`, `n_layers=4-5`, `dropout=0.4-0.5`
3. Agregar edge features al message passing (actualmente solo node features)
4. Usar learning rate warmup + cosine decay en lugar de ReduceLROnPlateau
5. Aumentar `max_epochs` a 500 con `early_stopping_patience=50`
6. Verificar que el featurizer genera las 45 features documentadas

**Resultado esperado:** AUC >= 0.80 con 5-fold CV

#### P2: Documentar honestamente las métricas (E3, E4)

**Problema:** Split por filas infla métricas; split por compuesto las colapsa.

**Acciones:**
1. En el notebook y reporte, presentar AMBOS splits con explicación clara
2. Reportar el split por compuesto como métrica principal
3. Explicar por qué los descriptores moleculares solos no predicen pChEMBL:
   - Mismo compuesto, distintas dianas/ensayos = distintos pChEMBL
   - Sin contexto de diana, la predicción es ambigua
4. Considerar que el split por filas (con features de ensayo) puede ser válido si se documenta el escenario de uso

#### P3: Implementar actualización de datos en dashboard (M1)

**Problema:** Cache LRU permanente, sin refresh.

**Acciones:**
```python
# Opción A: dcc.Interval para polling cada N segundos
dcc.Interval(id="refresh-interval", interval=30_000, n_intervals=0)

# Opción B: Invalidación por checksum de archivos
import hashlib

_file_checksums = {}

def load_with_refresh(path, loader_fn):
    current_hash = hashlib.md5(path.read_bytes()).hexdigest()
    if path not in _file_checksums or _file_checksums[path] != current_hash:
        _file_checksums[path] = current_hash
        loader_fn.cache_clear()
    return loader_fn()
```

**Recomendación:** Opción B (checksum) es más eficiente y no agrega tráfico innecesario.

#### P4: Completar entregables pendientes (E5, E6)

- Artículo IEEE: Compilar resultados de Flujos A-D + GIN/XAI en max 7 páginas
- Video: Grabación de pantalla del dashboard + narración del pipeline

### 5.2 Prioridad MEDIA — Mejoran calidad significativamente

#### P5: Desacoplar dashboard de PyTorch Geometric (M4)

**Problema:** `from src.data.dataset import TASK_NAMES` importa el módulo de dataset que requiere torch_geometric.

**Solución:**
```python
# dashboard/config.py — reemplazar import
TASK_NAMES = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-AtAD5", "SR-HSE", "SR-MMP", "SR-p53",
]
```

#### P6: Obtener datos INEC reales (M2)

**Problema:** Datos socioeconómicos son estimaciones generadas.

**Acciones:**
1. Descargar datos de INEC MAPI (https://www.inec.gob.pa/mapi/)
2. O documentar explícitamente que los datos son estimaciones con disclaimer en el dashboard

#### P7: Tratar colinealidad MW/heavy_atoms (M3)

**Acciones:**
1. Eliminar `heavy_atoms` del feature set (derivado linealmente de MW)
2. O aplicar PCA/VIF antes del modelado
3. Documentar decisión en notebook

#### P8: Limpiar FEATURE_COLS (M6)

**Acciones:**
```python
# chembl_preprocessing.py — remover features que nunca existen
FEATURE_COLS = [
    "mw_freebase", "alogp", "psa", "hba", "hbd",
    "aromatic_rings", "heavy_atoms", "rtb", "num_ro5_violations",
    # REMOVIDOS: cx_logp, cx_logd (100% NaN en ChEMBL extraction)
]
```

### 5.3 Prioridad BAJA — Nice to have

#### P9: Agregar comparativa baselines vs GIN al dashboard

Actualmente el dashboard no muestra los resultados de baselines ni del GIN comparativamente. Agregar una tabla resumen o gráfico de barras comparando AUC por modelo.

#### P10: Eliminar duplicados potenciales

Los registros con `potential_duplicate=1` deberían eliminarse o documentarse por qué se conservan.

#### P11: Agregar dcc.Loading a tabs pesados

El tab de Toxicidad GNN y Mapa Panamá pueden tardar en cargar. Agregar indicadores de loading mejora la UX.

#### P12: Health check endpoint

Agregar `/health` endpoint para monitoreo de deployment:
```python
@server.route("/health")
def health():
    return {"status": "ok", "chembl_rows": len(load_chembl())}
```

---

## 6. Resumen Ejecutivo

### Lo que funciona bien
- Pipeline de extracción ChEMBL (Flujo A) robusto con SQLite + API fallback
- EDA completo con missingno, UpSetPlot, imputación por familia
- Dashboard Dash con 4 tabs funcionales y 6+ controles interactivos
- Integración XAI con 98 SVGs servidos dinámicamente
- Mapa de Panamá con 76 distritos y choropleth
- Arquitectura modular (services/pages/config) bien separada
- Soporte dual: desarrollo local + deployment cloud (bundle mode)

### Lo que necesita atención
1. **Rendimiento del GIN** no alcanza objetivos — falta tuning y 5-fold CV
2. **Regresión no generaliza** a compuestos nuevos — necesita features de contexto
3. **Dashboard es estático** — no hay mecanismo de refresh de datos
4. **Datos INEC estimados** — deberían ser reales o documentados como estimaciones
5. **Artículo IEEE y video** pendientes como entregables del curso

### Riesgo para la JIC
El resultado principal del proyecto (GIN supera baselines) no se cumple con los datos actuales. El GIN (AUC 0.75) apenas supera al RF (AUC 0.74) por 0.006 puntos. Antes de presentar en la JIC, es fundamental:
1. Completar hyperparameter tuning del GIN
2. Ejecutar 5-fold CV para tener intervalos de confianza
3. Si no se logra AUC > 0.80, ajustar la narrativa de la hipótesis

---

*Generado por auditoría automatizada — 2026-06-20*
*Actualizado tras implementación de remedios — 2026-06-20*

---

## 7. Estado de implementación de remedios

| ID | Estado | Ubicación |
|----|--------|-----------|
| P1 | Infra lista | `config/config.yaml`, `run_gin_cv.py`, `make train-gin-cv` — **ejecutar CV para nuevos AUC** |
| P2 | OK | `docs/analisis_proyecto/METRICAS_EVALUACION.md`, `model_eval.json` |
| P3 | OK | `viz/services/dashboard/cache.py`, `POST /api/analytics/refresh` |
| P4 | Borrador | `docs/articulo_ieee/borrador.md`, `docs/video/guion.md` |
| P5 | OK | `viz/config.py` TASK_NAMES |
| P6 | OK | Disclaimer en `/panama/map` + API geo |
| P7/P8 | OK | `FEATURE_COLS` limpio, duplicados filtrados |
| P9 | OK | `/panama/models` comparativa baselines vs GIN |
| P10 | OK | `filter_potential_duplicates()` |
| P11 | OK | Loading overlays en EDA, toxicidad, mapa, comparativa |
| P12 | OK | `GET /health` en `viz/app.py` |
