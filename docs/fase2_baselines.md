# Fase II — Modelos Baseline

## 1. Qué son los baselines y por qué los necesitamos

Un **baseline** es un modelo de referencia que establece el piso de rendimiento. Si nuestra GNN no supera a los baselines, significa que toda la complejidad de la GNN no aporta valor y algo está mal.

Los 3 baselines son **modelos independientes y completos** — cada uno podría usarse en producción por sí solo. Los entrenamos bajo el **mismo protocolo** (mismos datos, mismo split, misma métrica) que la GNN para que la comparación sea justa.

### Regla de sanidad
Si el Random Forest no llega a AUC ~0.72-0.76 con scaffold split, hay un bug en el pipeline de datos. El script aborta automáticamente si AUC < 0.65.

---

## 2. Los 3 modelos baseline

### Baseline 1: Random Forest + Fingerprints Morgan ECFP4

**AUC esperado:** ~0.72-0.76 (scaffold split)

**Qué es un fingerprint Morgan (ECFP4):**
Un vector binario de 2048 bits que codifica qué subestructuras circulares existen en la molécula. Para cada átomo, mira los vecinos hasta radio 2 (ECFP4 = Extended Connectivity Fingerprint de radio 4 = diámetro 4 = radio 2) y genera un hash que se mapea a una posición del vector.

```
Molécula: c1ccccc1Cl  (clorobenceno)
     ↓ Morgan radius=2
Bit 457 = 1  (hay un cloro unido a benceno)
Bit 892 = 1  (hay un anillo aromático de 6)
Bit 1203 = 1 (hay un C aromático con vecino Cl)
... (2048 bits total, la mayoría son 0)
```

**Random Forest:** Entrena 800 árboles de decisión sobre estos fingerprints. Cada árbol vota "tóxico" o "no tóxico", y la fracción de votos da la probabilidad. Es robusto, no requiere GPU, y es el estándar clásico en quimioinformática.

**Detalles de implementación:**
- Entrena un RF separado por cada una de las 12 tareas
- Solo usa muestras con medición real (mask=True) para cada tarea
- Usa `class_weight='balanced_subsample'` para compensar desbalance
- Entrena con train+val (no tiene early stopping, así que usa todos los datos no-test)

### Baseline 2: MLP + Fingerprints Morgan ECFP4

**AUC esperado:** ~0.78

**Qué es:** Una red neuronal feedforward (Multi-Layer Perceptron) con 2 capas ocultas que recibe los mismos fingerprints de 2048 bits que el RF.

```
Fingerprint (2048) → Linear(2048, 512) → BN → ReLU → Dropout(0.3)
                   → Linear(512, 256)  → BN → ReLU → Dropout(0.3)
                   → Linear(256, 12)   → (logits para 12 tareas)
```

**Por qué suele superar al RF:** El MLP puede aprender combinaciones no lineales de bits del fingerprint que el RF no captura tan bien con sus divisiones por umbral.

**Detalles de implementación:**
- Usa MaskedBCELoss (misma función de pérdida que la GNN)
- Early stopping sobre AUC de validación
- Optimizador: Adam con lr=0.001
- 50 épocas máximas

### Baseline 3: SMILES2vec (CNN-GRU)

**AUC esperado:** ~0.80

**Qué es:** Un modelo de deep learning que lee el SMILES como texto, carácter por carácter, inspirado en modelos de NLP. Publicado por Goh et al. en KDD 2018.

```
SMILES texto: "c1ccccc1Cl"  (como secuencia de caracteres)
     ↓
Embedding: cada carácter → vector de 50 dimensiones
     ↓
Conv1D (filtros=192, kernel=3): extrae patrones locales de 3 caracteres
     ↓
GRU bidireccional capa 1 (224 unidades): captura dependencias secuenciales
     ↓
GRU bidireccional capa 2 (384 unidades): refina la representación
     ↓
Estado oculto final → Linear(768, 12) → (logits para 12 tareas)
```

**Por qué es mejor que el RF:** Aprende representaciones directamente del texto SMILES sin necesidad de calcular fingerprints manualmente. La arquitectura bidireccional puede capturar relaciones entre partes distantes de la molécula.

**Por qué la GNN debería superarlo:** SMILES es una representación lineal de una estructura 3D — el mismo grupo funcional puede aparecer en posiciones muy diferentes del texto. La GNN trabaja directamente sobre la topología del grafo, que es la representación nativa.

---

## 3. Protocolo de evaluación

### Datos de entrenamiento

| Modelo | Train | Val | Test |
|---|---|---|---|
| Random Forest | train + val (no tiene early stopping) | — | test |
| MLP | train | val (early stopping) | test |
| SMILES2vec | train | val (early stopping) | test |

### Métrica: AUC-ROC

AUC-ROC (Area Under the Receiver Operating Characteristic Curve) mide qué tan bien el modelo distingue entre moléculas activas e inactivas. 

- **AUC = 0.5**: modelo aleatorio (no aprendió nada)
- **AUC = 0.7**: modelo aceptable
- **AUC = 0.8**: modelo bueno
- **AUC = 1.0**: modelo perfecto

Se calcula por separado para cada una de las 12 tareas (porque cada tarea tiene diferentes moléculas medidas) y luego se promedia.

### Valores de referencia en la literatura

| Modelo | AUC reportado (MoleculeNet) | Split |
|---|---|---|
| Random Forest + ECFP4 | ~0.77 | Aleatorio |
| MLP + ECFP4 | ~0.79 | Aleatorio |
| SMILES2vec | ~0.81 | Aleatorio |
| GCN | ~0.83 | Aleatorio |

**Nota importante:** Los valores de MoleculeNet usan split **aleatorio**. Con scaffold split los AUC son **más bajos** (~3-5 puntos menos) porque la tarea es más difícil. Nuestros AUC esperados con scaffold son: RF ~0.72-0.76, MLP ~0.78, S2V ~0.80.

---

## 4. Ejecución

```bash
# Entrenar los 3 baselines
python scripts/train_baselines.py

# Modo verbose (ver progreso detallado)
python scripts/train_baselines.py -v

# Ver distribución de etiquetas por tarea
python scripts/train_baselines.py --label-stats
```

### Salida

El script genera `outputs/results/baseline_results.csv` con el AUC de cada modelo por tarea:

```csv
model,mean_auc,NR-AR,NR-AR-LBD,NR-AhR,...
RandomForest,0.743,0.681,0.712,0.823,...
MLP,0.779,0.723,0.748,0.851,...
SMILES2vec,0.801,0.745,0.761,0.867,...
```

---

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/models/baselines.py` | Definición de RF, MLP y SMILES2vec |
| `scripts/train_baselines.py` | Script que entrena los 3 y guarda resultados |
| `src/training/loss.py` | MaskedBCELoss (compartida con la GNN) |
| `src/evaluation/cross_validation.py` | evaluate_multitask_auc (compartida) |
