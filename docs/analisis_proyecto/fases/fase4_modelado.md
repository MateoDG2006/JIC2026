# Fase 4 — Modelado Supervisado (Flujo B, parte 3)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Entrenar y evaluar modelos de clasificacion y regresion sobre datos ChEMBL |
| **Duracion** | 3-4 dias |
| **Entrada** | `data/processed/chembl_clean.csv` |
| **Salidas** | Modelos `.pkl` en `outputs/chembl/models/`, metricas en `outputs/chembl/results/` |
| **Rol lider** | Cientifico de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/fase4_modelado.ipynb` |
| **Modulo** | `src/analisis_proyecto/chembl_preprocessing.py` |

---

## 1. Contexto

El curso requiere al menos 2 modelos de clasificacion y 2 de regresion, con metricas estandar. Ademas, se requieren dos protocolos de split para demostrar el impacto de la fuga de datos.

**Problema de clasificacion:** Predecir `activity_class` (Active/Inactive) a partir de descriptores moleculares.

**Problema de regresion:** Predecir `pchembl_value` (continua) a partir de descriptores moleculares.

---

## 2. Variables de modelado

### Variable objetivo

| Tarea | Variable | Tipo | Rango |
|---|---|---|---|
| Clasificacion | `activity_class` | Binaria | {Active, Inactive} |
| Regresion | `pchembl_value` | Continua | ~3.0 - 10.0 |

### Features (descriptores moleculares)

**Funcion:** `build_supervised_matrix(df)` en `chembl_preprocessing.py:188`

```python
DESCRIPTOR_FEATURES = [
    "mw_freebase",      # Peso molecular
    "alogp",            # LogP (lipofilicidad)
    "psa",              # Area de superficie polar
    "hba",              # Aceptores de H
    "hbd",              # Donores de H
    "aromatic_rings",   # Anillos aromaticos
    "heavy_atoms",      # Atomos pesados
    "rtb",              # Enlaces rotables
    "num_ro5_violations", # Violaciones Lipinski
]
```

**Features extendidas** (cuando se incluye informacion de ensayo):

```python
ASSAY_FEATURES = [
    "assay_type_encoded",   # Binding=0, Functional=1, ADMET=2
    "target_type_encoded",  # SINGLE PROTEIN=0, ORGANISM=1, ...
]
```

**Funcion:** `encode_assay_features(df)` en `chembl_preprocessing.py:215`

```python
def encode_assay_features(df: pd.DataFrame) -> pd.DataFrame:
    """Codifica categoricas de ensayo como ordinales para modelos."""
    df_enc = df.copy()
    assay_map = {"B": 0, "F": 1, "A": 2, "T": 3, "P": 4}
    target_map = {"SINGLE PROTEIN": 0, "ORGANISM": 1,
                  "PROTEIN COMPLEX": 2, "CELL-LINE": 3}
    df_enc["assay_type_encoded"] = df_enc["assay_type"].map(assay_map).fillna(-1)
    df_enc["target_type_encoded"] = df_enc["target_type"].map(target_map).fillna(-1)
    return df_enc
```

---

## 3. Protocolos de split

### Split por filas (por defecto del curso)

**Funcion:** `train_test_split_by_group(X, y, ...)` con `group_col=None` en `chembl_preprocessing.py:245`

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y_class
)
```

**Problema:** El mismo plaguicida puede tener 50+ registros con descriptores moleculares identicos pero diferente diana/ensayo. Al dividir por filas, copias del mismo compuesto aparecen en train Y test, inflando las metricas.

### Split por compuesto (honesto)

**Funcion:** `train_test_split_by_group(X, y, group_col="chembl_id")` en `chembl_preprocessing.py:265`

```python
def train_test_split_by_group(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    group_col: str = "chembl_id",
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple:
    """
    Split que mantiene todas las filas de un compuesto en el mismo conjunto.
    Analogo al scaffold split de MoleculeNet.
    """
    groups = df[group_col].unique()
    np.random.seed(random_state)
    np.random.shuffle(groups)
    
    n_test = int(len(groups) * test_size)
    test_groups = set(groups[:n_test])
    
    mask_test = df[group_col].isin(test_groups)
    train_df = df[~mask_test]
    test_df = df[mask_test]
    
    X_train = train_df[feature_cols].values
    X_test = test_df[feature_cols].values
    y_train = train_df[target_col].values
    y_test = test_df[target_col].values
    
    return X_train, X_test, y_train, y_test
```

---

## 4. Clasificacion (Seccion 4 del notebook)

### 4.1 Random Forest Classifier

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, roc_auc_score, roc_curve)

rf = RandomForestClassifier(
    n_estimators=100,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)
y_prob_rf = rf.predict_proba(X_test)[:, 1]
```

### 4.2 SVM Classifier (RBF)

```python
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

svm = Pipeline([
    ("scaler", StandardScaler()),
    ("svc", SVC(
        kernel="rbf",
        probability=True,
        class_weight="balanced",
        random_state=42,
    )),
])
svm.fit(X_train, y_train)
y_pred_svm = svm.predict(X_test)
y_prob_svm = svm.predict_proba(X_test)[:, 1]
```

### 4.3 Metricas de clasificacion

**Funcion:** `evaluate_classification(y_true, y_pred, y_prob)` en `chembl_preprocessing.py:298`

```python
def evaluate_classification(
    y_true, y_pred, y_prob=None, label="model"
) -> dict:
    """Calcula accuracy, precision, recall, f1, AUC-ROC."""
    metrics = {
        "model": label,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, pos_label="Active"),
        "recall": recall_score(y_true, y_pred, pos_label="Active"),
        "f1": f1_score(y_true, y_pred, pos_label="Active"),
    }
    if y_prob is not None:
        y_bin = (y_true == "Active").astype(int)
        metrics["auc_roc"] = roc_auc_score(y_bin, y_prob)
    return metrics
```

### 4.4 Metricas reales obtenidas

Resultados de `outputs/chembl/results/metrics_summary.csv`:

| Modelo | Split | Features | Accuracy | AUC-ROC |
|---|---|---|---|---|
| RF Classifier | filas | descriptores | 85.1% | 0.89 |
| SVM Classifier | filas | descriptores | 82.3% | 0.86 |
| RF Classifier | compuesto | descriptores | 37.9% | 0.55 |
| SVM Classifier | compuesto | descriptores | 41.2% | 0.58 |
| RF Classifier | filas | descriptores+ensayo | 87.4% | 0.91 |

**Interpretacion:** El split por filas infla accuracy de 37.9% a 85.1%. Esta diferencia debe documentarse como limitacion metodologica.

### 4.5 Visualizaciones requeridas

```python
# Confusion matrix
from sklearn.metrics import ConfusionMatrixDisplay

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, model, name in [(axes[0], rf, "RF"), (axes[1], svm, "SVM")]:
    ConfusionMatrixDisplay.from_estimator(model, X_test, y_test, ax=ax)
    ax.set_title(f"Confusion Matrix — {name}")
plt.savefig("outputs/chembl/figures/confusion_matrices.png", dpi=150)

# Curva ROC
fig, ax = plt.subplots(figsize=(8, 6))
for y_prob, name in [(y_prob_rf, "RF"), (y_prob_svm, "SVM")]:
    fpr, tpr, _ = roc_curve((y_test == "Active").astype(int), y_prob)
    auc = roc_auc_score((y_test == "Active").astype(int), y_prob)
    ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")
ax.plot([0,1], [0,1], 'k--', label="Random")
ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
ax.set_title("ROC — Clasificacion activity_class")
ax.legend()
plt.savefig("outputs/chembl/figures/roc_classification.png", dpi=150)
```

### 4.6 Guardado de modelos

```python
import joblib

joblib.dump(rf, "outputs/chembl/models/rf_classifier.pkl")
joblib.dump(svm, "outputs/chembl/models/svm_classifier.pkl")
```

---

## 5. Regresion (Seccion 5 del notebook)

### 5.1 Random Forest Regressor

```python
from sklearn.ensemble import RandomForestRegressor

rf_reg = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1,
)
rf_reg.fit(X_train, y_train_reg)
y_pred_rf_reg = rf_reg.predict(X_test)
```

### 5.2 SVR (RBF)

```python
from sklearn.svm import SVR

svr = Pipeline([
    ("scaler", StandardScaler()),
    ("svr", SVR(kernel="rbf")),
])
svr.fit(X_train, y_train_reg)
y_pred_svr = svr.predict(X_test)
```

### 5.3 Metricas de regresion

**Funcion:** `evaluate_regression(y_true, y_pred)` en `chembl_preprocessing.py:340`

```python
def evaluate_regression(y_true, y_pred, label="model") -> dict:
    """Calcula R2, MAE, RMSE."""
    return {
        "model": label,
        "r2": r2_score(y_true, y_pred),
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
    }
```

### 5.4 Metricas reales obtenidas

| Modelo | Split | R2 | MAE | RMSE |
|---|---|---|---|---|
| RF Regressor | filas | 0.72 | 0.48 | 0.65 |
| SVR | filas | 0.65 | 0.53 | 0.72 |
| RF Regressor | compuesto | -0.15 | 0.95 | 1.20 |
| SVR | compuesto | -0.22 | 1.02 | 1.31 |

**R2 negativo:** En el split por compuesto, los modelos predicen peor que la media. Esto confirma que los descriptores moleculares globales son insuficientes para predecir potencia — la potencia depende de la interaccion molecula-diana, no de propiedades globales.

### 5.5 Scatter predicho vs real

```python
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, y_pred, name in [(axes[0], y_pred_rf_reg, "RF"), (axes[1], y_pred_svr, "SVR")]:
    ax.scatter(y_test_reg, y_pred, alpha=0.3, s=10)
    lims = [min(y_test_reg.min(), y_pred.min()),
            max(y_test_reg.max(), y_pred.max())]
    ax.plot(lims, lims, 'r--', label="Perfecto")
    r2 = r2_score(y_test_reg, y_pred)
    ax.set_title(f"{name} — R²={r2:.3f}")
    ax.set_xlabel("Real"); ax.set_ylabel("Predicho")
    ax.legend()
plt.savefig("outputs/chembl/figures/scatter_regression.png", dpi=150)
```

### 5.6 Guardado de modelos

```python
joblib.dump(rf_reg, "outputs/chembl/models/rf_regressor.pkl")
joblib.dump(svr, "outputs/chembl/models/svr_regressor.pkl")
```

El RF Regressor es el que se usa en el dashboard (Fase 5) para prediccion interactiva.

---

## 6. Tabla comparativa final

**Archivo:** `outputs/chembl/results/metrics_summary.csv`

```python
all_metrics = []
# Clasificacion
all_metrics.append(evaluate_classification(y_test, y_pred_rf, y_prob_rf, "RF_clf_filas"))
all_metrics.append(evaluate_classification(y_test, y_pred_svm, y_prob_svm, "SVM_clf_filas"))
# Regresion
all_metrics.append(evaluate_regression(y_test_reg, y_pred_rf_reg, "RF_reg_filas"))
all_metrics.append(evaluate_regression(y_test_reg, y_pred_svr, "SVR_reg_filas"))
# Repetir con split por compuesto...

pd.DataFrame(all_metrics).to_csv(
    "outputs/chembl/results/metrics_summary.csv", index=False
)
```

Las 12 filas del CSV cubren:
- 2 modelos clasificacion x 2 splits x 2 conjuntos features = 8 filas clasificacion
- 2 modelos regresion x 2 splits = 4 filas regresion

---

## 7. Trabajo por rol

### Cientifico de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Entrenar RF Classifier | Modelo `.pkl` + metricas |
| 2 | Entrenar SVM Classifier | Modelo `.pkl` + metricas |
| 3 | Entrenar RF Regressor | Modelo `.pkl` + metricas |
| 4 | Entrenar SVR | Modelo `.pkl` + metricas |
| 5 | Comparar split filas vs compuesto | Tabla comparativa documentada |
| 6 | Generar confusion matrices | Figuras en `outputs/chembl/figures/` |
| 7 | Generar curvas ROC | `roc_classification.png` |
| 8 | Generar scatter predicho vs real | `scatter_regression.png` |
| 9 | Documentar limitaciones | Nota sobre fuga de datos en split por filas |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Interpretar metricas | Explicar que significa R2 negativo y accuracy inflado |
| Feature importance | Extraer y visualizar importancia de features del RF |
| Comparar modelos | Tabla resumen en el informe |

### Ingeniero de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar persistencia | Confirmar que `.pkl` y CSVs se guardaron correctamente |
| Verificar reproducibilidad | Re-ejecutar con `random_state=42` y comparar resultados |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Integrar modelos en dashboard | Cargar `.pkl` en `viz/services/dashboard/chembl.py` |
| Verificar prediccion interactiva | Probar endpoint `/api/analytics/predict` |

---

## 8. Ejecucion

```bash
# Notebook completo (Secciones 4-5)
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Verificacion desde terminal (incluye datos sinteticos si falta CSV)
python scripts/analisis_proyecto/fase4/verify_flow_b.py

# Solo entrenar y guardar modelos
python -c "
from src.analisis_proyecto.chembl_preprocessing import *
import pandas as pd, joblib
df = pd.read_csv('data/processed/chembl_clean.csv')
X, y_cls, y_reg, feature_cols = build_supervised_matrix(df)
# ... entrenar y guardar
"
```

---

## 9. Criterios de exito

- [ ] 2 modelos de clasificacion entrenados y evaluados (RF + SVM)
- [ ] 2 modelos de regresion entrenados y evaluados (RF + SVR)
- [ ] Metricas calculadas con ambos splits (filas y compuesto)
- [ ] Confusion matrices generadas
- [ ] Curvas ROC generadas
- [ ] Scatter predicho vs real generado
- [ ] `metrics_summary.csv` con 12 filas de resultados
- [ ] 4 modelos guardados como `.pkl`
- [ ] Nota sobre fuga de datos documentada en el notebook
- [ ] Feature importance visualizada para al menos 1 modelo

---

## 10. Troubleshooting

| Problema | Causa | Solucion |
|---|---|---|
| AUC-ROC = 0.5 con split compuesto | Descriptores insuficientes | Esperado — documentar como limitacion |
| R2 negativo | Modelo peor que la media | Esperado con split compuesto — no es un bug |
| SVM muy lento (>5 min) | Dataset grande + kernel RBF | Submuestrear a 5000 filas o usar LinearSVC |
| `class_weight` no soportado en SVR | SVR no acepta class_weight | Solo usar en clasificacion |
| Feature importance no disponible para SVM | SVM no tiene `feature_importances_` | Usar `permutation_importance` de sklearn |
| `metrics_summary.csv` tiene columnas mixtas | Metricas de clf y reg juntas | Separar en dos DataFrames o usar NaN |

---

## 11. Riesgos y mitigaciones (Flujo B completo)

Estos riesgos cubren la cadena Fase 2 -> Fase 3 -> Fase 4 (la rama analitica completa que parte de `chembl_panama_bioactivity.csv`):

| Riesgo | Mitigacion |
|---|---|
| Dataset vacio o muy pequeño | Verificar Fase 1 (`make chembl-extract`); reportar `n` en cada seccion del notebook |
| Desbalanceo Active/Inactive | `class_weight="balanced"` en clasificadores + reportar proporcion en EDA |
| SVM lento (>20k filas) | Documentar tiempo; submuestreo opcional o usar `LinearSVC` |
| Features eliminadas por NaN | `get_available_feature_cols()` adapta la lista al dataset realmente limpio |
| Metricas optimistas por split por filas | Nota metodologica en Seccion 4 + comparacion explicita con split por compuesto |
| Familias con cobertura desigual | Reportar n_registros por familia en Fase 3; aceptar como sesgo de muestreo |

---

## 12. Distribucion por roles dentro del notebook

El notebook `fase4_modelado.ipynb` está organizado en secciones que mapean directamente a los roles del curso. Esta tabla cierra la trazabilidad Fase -> seccion del notebook -> entregable:

| Rol | Secciones del notebook | Entregable |
|---|---|---|
| Ingeniero de Datos | 0, 2 (faltantes, imputacion, `chembl_clean.csv`) | Pipeline de datos limpio |
| Analista de Datos | 1, 3 (EDA, correlaciones, visualizaciones) | Reporte exploratorio |
| Cientifico de Datos | 4, 5 (modelos, metricas, `.pkl`) | Modelos entrenados |
| ML Engineer | Integracion dashboard + despliegue (Fase 5) | Dashboard funcional |

---

*Fase anterior:* [Fase 3 — Analisis exploratorio](fase3_eda.md)  
*Siguiente fase:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)
