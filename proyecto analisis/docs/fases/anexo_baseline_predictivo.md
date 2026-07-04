# Anexo — Baseline predictivo honesto (límite de descriptores clásicos)

> **AVISO — Este anexo NO forma parte del análisis descriptivo principal.**
> El estudio central del proyecto es **exploratorio, multivariado e inferencial** a nivel de
> compuesto (ver Fases 1–4): describe el espacio fisicoquímico, la promiscuidad biológica, los
> agrupamientos naturales y los contrastes de hipótesis entre familias. Este documento describe un
> **experimento adicional y completamente separado** (la pregunta P6 del rediseño). Su único fin es
> demostrar, de forma honesta, el **límite de los descriptores moleculares clásicos** para predecir
> potencia a compuestos no vistos, y servir de **puente al proyecto GNN de la JIC**. No es un producto,
> no es un logro de modelado y no debe leerse como tal.

---

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Cuantificar honestamente si un modelo simple predice `pchembl_median` a nivel de compuesto |
| **Naturaleza** | Anexo adicional y SEPARADO del análisis descriptivo/multivariado (no es la Fase 4) |
| **Duracion** | 1-2 dias |
| **Entrada** | `data/processed/compounds_features.csv` (107 compuestos) |
| **Salida** | `outputs/chembl/results/baseline_honest_metrics.csv` |
| **Rol lider** | Cientifico de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/anexo_baseline_predictivo.ipynb` (nuevo) |
| **Modulo** | `src/analisis_proyecto/chembl_preprocessing.py` |

---

## 1. Contexto

El proyecto original intentó **predecir toxicidad/potencia** con modelos clásicos (RF, SVM/SVR)
sobre descriptores moleculares y falló **por diseño, no por código**. El corpus tiene solo **107
compuestos únicos** repartidos en **3.608 filas de medición** (media ~34 mediciones/compuesto). Los
descriptores moleculares son **constantes dentro de cada compuesto** (`nunique = 1`): el modelo solo
"ve" 107 vectores de entrada distintos, sin importar cuántas filas existan.

Esto convierte a la predicción en un caso de estudio sobre **fuga de datos**, no en un producto. Por
eso el baseline vive fuera del análisis principal, en este anexo:

- El **análisis descriptivo/multivariado** (Fases 1–4) es el corazón del proyecto y responde P1–P5.
- El **baseline predictivo** (P6) es un experimento de control que reporta un **límite**, no un
  resultado de modelado que celebrar.

**Pregunta P6:** ¿Un modelo simple ordena/predice la potencia mediana (`pchembl_median`) de un
compuesto a partir de sus descriptores, cuando la validación se hace **por compuesto**?

**Respuesta esperada (honesta):** No. El modelo **no generaliza** a compuestos no vistos.

---

## 2. Diseño experimental

### 2.1 Unidad de análisis

| Elemento | Valor |
|---|---|
| **Unidad** | Compuesto (no fila/medición) |
| **N** | 107 compuestos únicos |
| **Target** | `pchembl_median` (potencia mediana consolidada por compuesto) |
| **Features** | Los 9 descriptores moleculares |

La unidad es el **compuesto**, no la medición. Cada compuesto aporta exactamente una fila a la matriz
de modelado, tomada de `data/processed/compounds_features.csv`.

### 2.2 Features (descriptores moleculares)

```python
DESCRIPTOR_FEATURES = [
    "mw_freebase",        # Peso molecular
    "alogp",              # LogP (lipofilicidad)
    "psa",                # Area de superficie polar
    "hba",                # Aceptores de H
    "hbd",                # Donores de H
    "aromatic_rings",     # Anillos aromaticos
    "rtb",                # Enlaces rotables
    "heavy_atoms",        # Atomos pesados
    "num_ro5_violations", # Violaciones Lipinski
]
```

Estos descriptores ya vienen consolidados por compuesto en `compounds_features.csv` (son constantes
dentro de cada `chembl_id`, de modo que la agregación no pierde información en las features).

### 2.3 Modelos simples

| Modelo | Rol |
|---|---|
| `RandomForestRegressor` | Modelo principal del baseline (no lineal) |
| `Ridge` (opcional) | Baseline lineal de contraste |

No se busca ajustar hiperparámetros ni exprimir el rendimiento: se trata de mostrar el techo real de
la señal disponible con estos descriptores.

### 2.4 Validación — ÚNICAMENTE por compuesto

**Regla de honestidad (no negociable):** con la unidad = compuesto, el split por filas **no existe**
como opción válida en este anexo. Se valida solo por grupo:

- **Split por grupo** con `train_test_split_by_group(..., group_col="chembl_id")` (ya existe en el
  módulo), garantizando que ningún compuesto aparezca simultáneamente en train y test.
- **K-fold por grupo** con `GroupKFold` (validación cruzada agrupada) para estabilizar la métrica
  frente a la varianza del split único con solo 107 compuestos.

> Como en `compounds_features.csv` hay una fila por compuesto, el split por grupo equivale
> naturalmente a un split limpio por compuesto. El punto es dejar el protocolo explícito y
> reutilizar `train_test_split_by_group` / `GroupKFold` para que sea imposible reintroducir fuga.

### 2.5 Métricas

| Métrica | Función |
|---|---|
| R² | `evaluate_regression(y_true, y_pred)` en `chembl_preprocessing.py` |
| MAE | idem |
| RMSE | idem |

Función nueva a nombrar en el módulo: `run_honest_baseline(compounds_df) -> pd.DataFrame`
**(nueva función — a implementar)**, que orquesta split por compuesto + K-fold por grupo y escribe
`baseline_honest_metrics.csv`.

---

## 3. Resultado esperado (honesto)

El resultado esperado, coherente con el diagnóstico del corpus, es un **R² bajo o negativo** en el
split por compuesto: el modelo predice **peor que la media** sobre compuestos no vistos y, por tanto,
**no generaliza**. En el proyecto original, bajo split por compuesto, el R²_test observado fue
**negativo (rango aproximado -0.25 a -1.13)**.

### 3.1 El contraste que revela la verdad

| Protocolo | R² (esperado) | ¿Válido? | Por qué |
|---|---|---|---|
| Split por FILAS (a nivel medición) | Alto, ~0.5–0.6 | **NO — fuga de datos** | Las mismas moléculas aparecen en train y test; como los descriptores son constantes por compuesto, el modelo "memoriza" filas ya vistas |
| Split por COMPUESTO (este anexo) | Bajo o **negativo** | **Sí — honesto** | Ningún compuesto se comparte; mide generalización real a moléculas nuevas |

El split por filas **infla** artificialmente la métrica porque el modelo reencuentra en test los
mismos 107 vectores de entrada que ya vio en train. Al pasar a split por compuesto, esa ventaja
desaparece y aflora la verdad: **8-9 descriptores globales no contienen suficiente señal para
ordenar potencia entre moléculas distintas**.

> Los números ~0.5–0.6 (filas) y negativo (compuesto) se citan como **referencia del diagnóstico
> honesto**, no como métricas a "conseguir". En el notebook se recalculan ambos y se documenta
> explícitamente la fuga.

---

## 4. Conclusión y puente al JIC

Con **107 compuestos** y solo **8-9 descriptores moleculares** (constantes por compuesto) **no hay
señal suficiente** para predecir potencia a compuestos no vistos. Esto no es un fallo de
implementación: es el **límite intrínseco de una representación pobre** de la molécula. La potencia
depende de la interacción molécula–diana y de la topología estructural fina, que un puñado de
descriptores globales no captura.

Este resultado **motiva y justifica** el salto a representaciones más ricas:

- **Grafos moleculares** (átomos como nodos, enlaces como aristas) en lugar de descriptores escalares.
- **Graph Neural Networks (GNN, arquitectura GIN)** que aprenden la representación directamente del
  grafo — el enfoque central del **proyecto JIC**.

Así, este anexo cierra honestamente la rama predictiva del estudio descriptivo y entrega el testigo
al proyecto de investigación de la JIC.

---

## 5. Trabajo por rol

### Cientifico de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Cargar `compounds_features.csv` (107 filas) | Matriz de modelado a nivel compuesto |
| 2 | Entrenar `RandomForestRegressor` con split por compuesto | Métricas honestas |
| 3 | (Opcional) Entrenar `Ridge` como baseline lineal | Métricas de contraste |
| 4 | Ejecutar `GroupKFold` para estabilizar R²/MAE/RMSE | Métricas promediadas por fold |
| 5 | Reproducir el FALSO split por filas y medir la inflación | Tabla comparativa filas vs compuesto |
| 6 | Documentar la fuga de datos y el R² negativo | Nota metodológica en el notebook |
| 7 | Escribir el puente al proyecto GNN/JIC | Sección de conclusión |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Interpretar métricas | Explicar qué significa un R² negativo (peor que predecir la media) |
| Contrastar protocolos | Redactar por qué el split por filas es fuga y el de compuesto es honesto |

### Ingeniero de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar unidad = compuesto | Confirmar 107 filas y ausencia de compuestos duplicados en la matriz |
| Verificar no-fuga | Confirmar que ningún `chembl_id` cae en train y test simultáneamente |
| Verificar persistencia | Confirmar `baseline_honest_metrics.csv` escrito correctamente |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Enmarcar el límite | Traducir "no generaliza" al lenguaje de la motivación GNN del JIC |
| No integrar en dashboard | Este baseline NO se despliega: es diagnóstico, no producto |

---

## 6. Ejecucion

```bash
# Notebook completo del anexo
jupyter notebook "notebooks/proyecto analisis de datos/anexo_baseline_predictivo.ipynb"

# Ejecucion rapida desde terminal (esquema)
python -c "
from src.analisis_proyecto.chembl_preprocessing import (
    train_test_split_by_group, evaluate_regression,
)
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
import pandas as pd, numpy as np

df = pd.read_csv('data/processed/compounds_features.csv')   # 107 compuestos
features = ['mw_freebase','alogp','psa','hba','hbd',
            'aromatic_rings','rtb','heavy_atoms','num_ro5_violations']

# --- Split HONESTO por compuesto ---
X_tr, X_te, y_tr, y_te = train_test_split_by_group(
    df, target_col='pchembl_median', feature_cols=features,
    group_col='chembl_id', test_size=0.2, random_state=42,
)
rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1).fit(X_tr, y_tr)
honest = evaluate_regression(y_te, rf.predict(X_te), 'RF_compuesto')
print('HONESTO (compuesto):', honest)   # R2 esperado: bajo o NEGATIVO

# Guardar metricas honestas
pd.DataFrame([honest]).to_csv(
    'outputs/chembl/results/baseline_honest_metrics.csv', index=False
)
"
```

---

## 7. Criterios de exito

- [ ] `compounds_features.csv` cargado con **107 filas** (unidad = compuesto)
- [ ] `RandomForestRegressor` entrenado con **split por compuesto**
- [ ] (Opcional) `Ridge` entrenado como baseline lineal
- [ ] Validación cruzada `GroupKFold` ejecutada (métricas promediadas por fold)
- [ ] R², MAE y RMSE reportados para el split por compuesto (honesto)
- [ ] **Ambas métricas reportadas lado a lado**: split por compuesto (honesto) vs FALSO split por filas
- [ ] Diferencia documentada explícitamente como **fuga de datos** (no como mejora del modelo)
- [ ] R² por compuesto confirmado como **bajo o negativo** → el modelo no generaliza
- [ ] `outputs/chembl/results/baseline_honest_metrics.csv` escrito
- [ ] Sección de puente al proyecto GNN/JIC redactada (justifica grafos moleculares)
- [ ] Verificado que ningún `chembl_id` aparece en train y test a la vez

---

## 8. Troubleshooting

| Problema | Causa | Solucion |
|---|---|---|
| R² negativo en split por compuesto | Modelo peor que la media | **Esperado** — es el hallazgo del anexo, no un bug |
| R² alto (~0.5–0.6) "sospechosamente bueno" | Se usó split por filas | Fuga de datos — cambiar a `group_col="chembl_id"` |
| `compounds_features.csv` no existe | Falta la consolidación de Fase 2 | Generar con `build_compound_features(activities_df)` (Fase 2) |
| Varianza alta entre ejecuciones | Solo 107 compuestos, split único inestable | Usar `GroupKFold` y promediar folds |
| Menos de 107 filas en la matriz | Duplicados o NaN en descriptores | Verificar dedup y descriptores completos en Fase 2 |
| Tentación de "mejorar" el R² | Confundir el objetivo del anexo | El objetivo es mostrar el LÍMITE, no maximizar la métrica |

---

## 9. Relación con el resto del proyecto

Este anexo es **complementario y subordinado** al análisis principal:

- El análisis **descriptivo, multivariado e inferencial** (Fases 1–4) responde las preguntas
  centrales P1–P5 y constituye el producto del proyecto de curso.
- Este anexo responde **solo P6** y lo hace como **control negativo**: confirma que la vía predictiva
  clásica no es viable con estos datos, cerrando el argumento a favor del enfoque de grafos del JIC.

---

*Documento principal relacionado:* [Fase 4 — Análisis multivariado y contraste de hipótesis](fase4_modelado.md)
*Índice del proyecto:* [README — Proyecto de Análisis de Datos](../README.md)
