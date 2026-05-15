# Explainable AI (XAI)

**Módulos:** `src/xai/gnn_explainer.py`, `src/xai/grad_cam.py`, `src/xai/visualizer.py`, `src/evaluation/chemical_coherence.py`  
**Fase:** IV — Explainable AI (Semanas 7–8)

---

## Descripción

Dos técnicas complementarias para explicar qué átomos del grafo molecular son responsables de la predicción de toxicidad: **GNNExplainer** (optimización de máscara por molécula) y **Grad-CAM** (gradientes sobre activaciones de la última capa GIN). Las explicaciones se visualizan coloreando la estructura molecular y se validan contra conocimiento químico documentado.

---

## GNNExplainer (`gnn_explainer.py`)

### Principio

Para cada molécula, optimiza una máscara sobre nodos y aristas que maximiza la predicción del modelo con el subgrafo enmascarado. Identifica el subgrafo mínimo que explica la predicción.

```python
from torch_geometric.explain import Explainer, GNNExplainer as PyGExplainer

explainer = Explainer(
    model          = trained_model,
    algorithm      = PyGExplainer(epochs=200, lr=0.01),
    explanation_type = 'model',
    node_mask_type = 'attributes',    # máscara por feature de nodo
    edge_mask_type = 'object',        # máscara escalar por arista
    model_config   = dict(
        mode         = 'binary_classification',
        task_level   = 'graph',
        return_type  = 'raw',         # logits
    ),
)
```

### Salida por molécula

```python
explanation = explainer(x, edge_index, batch=..., target=task_index)

node_importance = explanation.node_mask.squeeze()  # (num_atoms,) — [0,1]
edge_importance = explanation.edge_mask             # (num_edges,) — [0,1]
```

---

## Grad-CAM para grafos (`grad_cam.py`)

### Principio

Calcula la importancia de cada nodo usando gradientes de la predicción respecto a las activaciones de la última capa GIN. No requiere optimización por molécula — es más rápido que GNNExplainer.

```
α_k     = (1/N) Σ_v [ ∂y_c / ∂A_kv ]       ← importancia de canal k
cam(v)  = ReLU( Σ_k [ α_k × A_kv ] )        ← importancia del nodo v
cam     normalizado a [0, 1]
```

### Flujo de cómputo

```
1. Registrar hooks de forward y backward en la última capa GINLayer
2. Forward pass → guardar activaciones A
3. Backward para la tarea objetivo → guardar gradientes ∂y/∂A
4. Calcular α_k = mean(gradientes) sobre todos los nodos
5. cam(v) = ReLU( Σ α_k × A_kv )
6. Normalizar a [0,1]
7. Limpiar hooks
```

---

## GNNExplainer vs Grad-CAM

| Aspecto | GNNExplainer | Grad-CAM |
|---|---|---|
| Velocidad | Lento (200 épocas/molécula) | Rápido (1 forward+backward) |
| Granularidad | Nodo + arista | Solo nodo |
| Fidelidad | Alta (optimización directa) | Media (aproximación lineal) |
| Uso recomendado | Análisis detallado (20+ moléculas) | Screening rápido del corpus |
| Target coherencia | Precision@3 > 80% | Correlación Spearman > 0.70 con GNNExp |

---

## Visualización molecular (`visualizer.py`)

Genera imágenes SVG coloreando cada átomo según su importancia XAI usando la paleta `YlOrRd` (amarillo → naranja → rojo).

```python
svg = draw_molecule_with_importance(
    smiles          = "CCc1ccc(N)cc1",
    node_importance = cam_values,      # array (num_atoms,)
    title           = "Clorpirifos — NR-AhR",
    save_path       = "outputs/xai/figures/chlorpyrifos_NR-AhR.svg"
)
```

Las imágenes se guardan en `outputs/xai/figures/` (SVG por molécula × tarea).

---

## Validación química (`chemical_coherence.py`)

### Hipótesis por vía Tox21

Los grupos funcionales esperados para cada diana biológica, basados en literatura química:

| Vía | Grupos funcionales esperados | Clase de agroquímico |
|---|---|---|
| NR-AR | ligandos esteroideos: `-OH`, `-NH2`, ésteres | Triazinas, azoles |
| NR-ER | fenoles: `c-OH`, `-NH2` | Organofosforados |
| NR-AhR | aromáticos planos: benceno, piridina | Organoclorados |
| NR-Aromatase | anillos azol + `-Cl` | Fungicidas azólicos |
| SR-ARE | electrófilos: `P=S`, `N+=O`, `C=C` | Organofosforados, glifosato |
| SR-p53 | genotóxicos: `-NO2`, `C=C`, `-Cl` | Fungicidas, herbicidas |
| NR-PPAR-γ | ácidos grasos: `-COOH`, cadenas largas | Herbicidas |

### Métricas de coherencia

**Precision@k**: porcentaje de moléculas donde al menos `k` de los `k` átomos más importantes pertenecen al grupo funcional correcto para esa vía.

| Métrica | Objetivo |
|---|---|
| Precision@1 | > 65% |
| Precision@3 | > 80% |
| Fidelidad del subgrafo | AUC (top-5 átomos) vs AUC completo: diferencia < 0.05 |
| Coherencia GNNExp vs GradCAM | Correlación de Spearman > 0.70 |

---

## Casos de estudio prioritarios

| Compuesto | Vía esperada | Grupo funcional clave |
|---|---|---|
| **Clorpirifos** | SR-ARE, NR-AhR | Fosforotioato `P=S` |
| **Atrazina** | NR-AR, NR-ER | Anillo triazina con `-Cl` |
| **Tebuconazol** | NR-Aromatase, NR-PPAR-γ | Anillo triazol + `-Cl` |
| **Cipermetrina** | SR-HSE, SR-MMP | Éster + grupo ciano `CN` |
| **Paraquat** | SR-ARE, SR-p53 | Catión bipiridilo |
| **Glifosato** | SR-ARE | Fosfonato + amina |

---

## Flujo de análisis completo

```
1. Cargar modelo entrenado (best_gin_model.pt)
2. Para cada plaguicida en corpus panameño:
   a. Construir grafo molecular (featurizer)
   b. Predecir → identificar diana con mayor probabilidad
   c. GNNExplainer → node_importance, edge_importance
   d. Grad-CAM     → cam_values (verificación cruzada)
   e. Visualizar   → SVG con colores de importancia
   f. precision@3  → validar contra grupos funcionales esperados
3. Calcular métricas agregadas sobre corpus
4. Generar galería de imágenes + tabla de coherencia
```

---

## Archivos de salida

```
outputs/xai/
├── explanations/
│   ├── chlorpyrifos_NR-AhR_gnnexpl.pt      # máscaras GNNExplainer
│   ├── atrazine_NR-AR_gnnexpl.pt
│   └── ...
└── figures/
    ├── chlorpyrifos_NR-AhR.svg              # visualización coloreada
    ├── atrazine_NR-AR.svg
    └── ...
```

---

## Entregables

- [ ] GNNExplainer implementado con PyG Explainer API
- [ ] Grad-CAM implementado con hooks de activación/gradiente
- [ ] Visualizaciones generadas para 20+ moléculas del corpus panameño
- [ ] Precision@1, @3, @5 calculadas para GNNExplainer y Grad-CAM
- [ ] Comparación de coherencia: GNNExplainer vs Grad-CAM documentada
- [ ] Galería de imágenes en `outputs/xai/figures/`
- [ ] Al menos 6 casos de estudio detallados (molécula → predicción → explicación → validación química)
- [ ] Validación GHS: correlacionar predicciones con etiquetas H300-H361 de `pubchem_ghs_labels.csv`

---

## Dependencias

```
torch>=2.0
torch_geometric>=2.4    # Explainer, GNNExplainer
captum                  # Grad-CAM alternativo
rdkit>=2023.09          # Draw, rdMolDraw2D
matplotlib              # visualización
numpy
```
