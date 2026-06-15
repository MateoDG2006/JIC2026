# Fase III — Modelo GNN-GIN

## 1. Qué es una GNN y por qué la necesitamos

### El problema

Queremos predecir si una molécula es tóxica analizando su estructura. Los baselines (RF, MLP) usan fingerprints — vectores fijos que **resumen** la molécula pero pierden la topología (qué átomo está conectado a cuál). La GNN trabaja directamente sobre el **grafo molecular**, preservando toda la información estructural.

### Cómo funciona una GNN (Message Passing)

La idea central es simple: cada átomo "habla" con sus vecinos y actualiza su representación basándose en lo que recibe.

```
Iteración 1: Cada átomo mira a sus vecinos directos
  → "Soy un carbono conectado a un cloro y un nitrógeno"

Iteración 2: Cada átomo ahora incluye info de vecinos de vecinos
  → "Soy un carbono conectado a un cloro, y ese cloro está en un anillo"

Iteración 3: La información se propaga a 3 enlaces de distancia
  → "Soy parte de un grupo fosforotioato (P=S) cerca de un anillo clorado"
```

Después de L iteraciones, cada átomo tiene una representación que captura su vecindario químico completo hasta radio L.

---

## 2. Por qué GIN y no GCN o GAT

### GCN (Graph Convolutional Network)
- Agrega vecinos con **promedio ponderado**
- Problema: no distingue entre "1 vecino con valor 6" y "3 vecinos con valor 2" (ambos dan promedio 2)
- Menor expresividad teórica

### GAT (Graph Attention Network)
- Usa **atención** para ponderar vecinos
- Más parámetros, más lento de entrenar
- Los pesos de atención son interpretables pero menos precisos que GNNExplainer para XAI

### GIN (Graph Isomorphism Network)
- Agrega vecinos con **suma** (preserva multiplicidad)
- Añade factor (1 + ε) al nodo central para distinguirlo de sus vecinos
- **Máxima expresividad** dentro de la clase 1-WL (demostrado por Xu et al., ICLR 2019)
- Equivale al test de isomorfismo de Weisfeiler-Lehman — puede distinguir grafos que GCN confunde

```
Fórmula GIN:
  h_v^(l) = MLP( (1 + ε) · h_v^(l-1)  +  Σ h_u^(l-1) )
                   ↑                        ↑
              nodo actual              suma de vecinos
```

### Por qué GINEConv (no GINConv)

GINConv **ignora** las features de los enlaces. Pero en química, el tipo de enlace es crucial:
- Un enlace simple C-C vs doble C=C cambia completamente las propiedades
- La conjugación y la estereoquímica afectan la toxicidad

GINEConv extiende GIN para incorporar las 9 features de cada enlace en la agregación.

---

## 3. Arquitectura completa

```
                    SMILES string
                         │
                         ▼
            ┌─────────────────────────┐
            │   RDKit: SMILES → Grafo │
            │   45 features/nodo      │
            │    9 features/arista    │
            └────────────┬────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────┐
    │  BLOQUE 1: Proyección Inicial               │
    │                                             │
    │  Linear(45 → 128) → BatchNorm → ReLU        │
    │                                             │
    │  Propósito: proyectar los 45 features de    │
    │  cada átomo al espacio oculto de 128 dims   │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │  BLOQUE 2: Message Passing (3 capas GIN)    │
    │                                             │
    │  Para cada capa l = 1, 2, 3:                │
    │                                             │
    │    h_v = MLP( (1+ε)·h_v + Σ h_u·e_uv )     │
    │          │                                  │
    │          ▼                                  │
    │    BatchNorm → ReLU → Dropout(0.3)          │
    │          │                                  │
    │          ▼                                  │
    │    h_v = h_v + h_v_anterior  ← residual     │
    │                                             │
    │  Después de 3 capas, cada átomo "sabe"      │
    │  sobre su vecindario hasta radio 3          │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │  BLOQUE 3: Readout Global                   │
    │                                             │
    │  h_G = CONCAT( mean_pool, max_pool )        │
    │                                             │
    │  mean_pool: promedio de todos los átomos    │
    │    → captura la composición general          │
    │  max_pool: máximo por canal                 │
    │    → captura los átomos más "extremos"      │
    │                                             │
    │  Resultado: vector de 256 dims (128+128)    │
    │  que representa toda la molécula            │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │  BLOQUE 4: Clasificador Multitarea          │
    │                                             │
    │  Linear(256 → 128) → BN → ReLU → Dropout   │
    │  Linear(128 → 64)  → BN → ReLU → Dropout   │
    │  Linear(64 → 12)   → Sigmoid                │
    │                                             │
    │  Salida: 12 probabilidades ∈ [0,1]          │
    │  una por cada diana biológica Tox21         │
    └─────────────────────────────────────────────┘
```

### Conexiones residuales

Sin conexiones residuales, después de muchas capas GIN todos los nodos convergen a representaciones similares (**over-smoothing**). La conexión residual `h_v = h_v + h_v_anterior` permite que cada capa **refine** la representación en vez de reemplazarla.

### Por qué mean + max pooling

- **Mean pooling solo**: si una molécula tiene 50 átomos y solo 1 es tóxico, el promedio "diluye" la señal del átomo tóxico
- **Max pooling solo**: puede ser inestable y perder información de la composición general
- **Mean + max**: captura ambos — la composición global Y los átomos extremos

---

## 4. Entrenamiento

### Función de pérdida: MaskedBCELoss

Binary Cross Entropy con máscara para datos faltantes:
1. Calcula la pérdida para TODAS las 12 tareas
2. Multiplica por la máscara (0 donde no hay medición)
3. Promedia solo sobre las posiciones con medición real

### Optimización

| Parámetro | Valor | Por qué |
|---|---|---|
| Optimizador | Adam | Estándar para deep learning, adaptativo |
| Learning rate | 0.001 | Valor típico para GNN |
| Gradient clipping | norma ≤ 1.0 | Evita explosión de gradientes en grafos |
| Batch size | 32 | Balance entre estabilidad y memoria |

### Regularización

| Técnica | Valor | Efecto |
|---|---|---|
| Dropout | 0.3 | Apaga 30% de neuronas aleatoriamente → evita overfitting |
| BatchNorm | en cada capa | Estabiliza el entrenamiento, permite LR más alto |
| Early stopping | paciencia 50 | Detiene si val_AUC no mejora por 50 épocas |
| LR scheduler | factor 0.5, paciencia 20 | Reduce LR a la mitad si no mejora por 20 épocas |

### 5-Fold Cross-Validation

Para obtener una estimación robusta del rendimiento:

1. Tomar los datos de train+val
2. Crear 5 particiones por scaffold (ningún scaffold cruzado entre folds)
3. Para cada fold: entrenar con 4/5, validar con 1/5, evaluar en test
4. Reportar: media ± desviación estándar del AUC sobre los 5 folds

---

## 5. Métricas objetivo

| Métrica | Mínimo | Ideal |
|---|---|---|
| AUC-ROC promedio (12 tareas) | > 0.82 | > 0.84 |
| AUC-ROC por tarea individual | > 0.75 en todas | > 0.80 en todas |
| Desviación estándar entre folds | < 0.02 | < 0.015 |
| Supera RF baseline | Obligatorio | +0.05 AUC |
| Supera SMILES2vec baseline | Objetivo principal | +0.02 AUC |

### Ablation study planificado

| Variante | Cambio | Propósito |
|---|---|---|
| hidden_dim=256 | Duplicar dimensión oculta | ¿Más capacidad mejora AUC? |
| n_layers=5 | 5 capas en vez de 3 | ¿Mayor radio de vecindario ayuda? |
| Sin residual | Quitar conexiones residuales | Confirmar que evitan over-smoothing |
| Sin edge features | GINConv en vez de GINEConv | Confirmar que los enlaces importan |

---

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/models/gin.py` | Arquitectura GINToxicity (GINEConv + residual) |
| `src/training/trainer.py` | Loop de entrenamiento con early stopping |
| `src/training/loss.py` | MaskedBCELoss (ignora NaN + pos_weight) |
| `src/evaluation/cross_validation.py` | AUC-ROC + scaffold folds para 5-fold CV |
| `config/config.yaml` | Todos los hiperparámetros centralizados |
