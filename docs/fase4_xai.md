# Fase IV — Explainable AI (XAI)

## 1. Por qué necesitamos explicabilidad

El modelo GNN-GIN predice que una molécula es tóxica, pero no dice **por qué**. Para un regulador del MIDA o del MINSA, un número (P=0.87 de toxicidad) no es suficiente — necesita saber:

- **¿Qué parte de la molécula causa la toxicidad?**
- **¿El modelo está mirando los átomos correctos?**
- **¿La predicción es coherente con lo que se sabe en la literatura?**

La XAI (Explainable AI) responde estas preguntas identificando qué **átomos y enlaces** del grafo molecular son los más importantes para cada predicción.

---

## 2. Los dos métodos de explicación

Usamos dos métodos complementarios porque cada uno tiene fortalezas y debilidades:

### GNNExplainer — Optimización de máscara

**Publicación:** Ying et al., "GNNExplainer: Generating Explanations for Graph Neural Networks", NeurIPS 2019.

**Idea central:** Encontrar el **subgrafo más pequeño** que produce la misma predicción que el grafo completo.

**Cómo funciona paso a paso:**

```
1. Tomar el grafo completo de la molécula
   → El modelo predice P(tóxico) = 0.87 para SR-ARE

2. Crear una máscara continua M ∈ [0,1] para cada nodo y arista
   → Inicialmente M ≈ 0.5 para todos (incertidumbre)

3. Aplicar la máscara al grafo:
   → features_masked = features_originales × M
   → Los átomos con M≈0 se "apagan", los de M≈1 se mantienen

4. Pasar el grafo enmascarado por el modelo (congelado, sin entrenar)
   → El modelo predice P(tóxico|máscara) = ???

5. Optimizar la máscara minimizando:
   Pérdida = -log(P(tóxico|máscara))  +  λ·||M||₁
              ↑                           ↑
   "que la predicción se mantenga"   "que la máscara use pocos nodos"
   (fidelidad)                       (parsimonia)

6. Repetir pasos 3-5 durante 200 iteraciones de optimización
   → La máscara converge: M≈1 en átomos importantes, M≈0 en los demás

7. Resultado: los átomos con M > 0.5 son los "responsables" de la predicción
```

**Ventaja:** Muy preciso — encuentra exactamente el subgrafo mínimo necesario.
**Desventaja:** Lento — 200 forward passes por molécula por tarea.

**Detalle técnico — _SingleTaskWrapper:**
GNNExplainer de PyG espera un modelo con **una sola salida**. Pero GINToxicity tiene 12 salidas (una por tarea). El `_SingleTaskWrapper` envuelve el modelo para que solo retorne el logit de la tarea que queremos explicar:

```python
class _SingleTaskWrapper(nn.Module):
    def __init__(self, model, task_index):
        self.model = model
        self.task_index = task_index

    def forward(self, x, edge_index, batch, edge_attr=None):
        logits = self.model(x, edge_index, batch, edge_attr=edge_attr)
        return logits[:, self.task_index].unsqueeze(-1)  # solo 1 salida
```

### Grad-CAM para grafos — Gradientes × Activaciones

**Publicación original:** Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks", ICCV 2017. Adaptado aquí para grafos.

**Idea central:** Los átomos que más contribuyen a la predicción son aquellos que activaron fuertemente canales que el modelo considera importantes para esa tarea.

**Cómo funciona paso a paso:**

```
1. Forward pass: pasar la molécula por el modelo
   → Grabar las ACTIVACIONES de la última capa GIN
   → Activación[v][k] = "qué tan fuerte activó el átomo v en el canal k"

2. Backward pass: calcular el gradiente de la predicción
   → Gradiente[v][k] = "si aumento la activación del canal k en el átomo v,
                         ¿cuánto cambia la predicción?"

3. Para cada canal k:
   α[k] = promedio del gradiente sobre todos los átomos
   → "¿qué tan importante es este canal k para la predicción?"

4. Para cada átomo v:
   importancia(v) = ReLU( Σ_k  α[k] × activación[v][k] )
   → "este átomo activó canales importantes"

5. Normalizar a [0, 1] y reportar
```

**Ventaja:** Muy rápido — un solo forward + backward por molécula.
**Desventaja:** Más ruidoso que GNNExplainer, puede señalar átomos "cerca" del importante.

**Detalle técnico — ¿Por qué model.train() en vez de model.eval()?**
En modo eval, BatchNorm usa estadísticas "running" (promedio de todo el entrenamiento) que suavizan los gradientes y reducen la calidad de las explicaciones. En modo train, BatchNorm usa las estadísticas del batch actual, dando gradientes más informativos.

---

## 3. Visualización molecular

Una vez que tenemos la importancia de cada átomo, la visualizamos coloreando la molécula:

```
Importancia alta (≥ 0.7)  →  Rojo intenso     → "Este átomo causa toxicidad"
Importancia media (0.3-0.7) →  Naranja/Amarillo → "Contribuye parcialmente"
Importancia baja (< 0.3)  →  Amarillo claro    → "No relevante"
```

Se genera un SVG (imagen vectorial) para cada molécula usando RDKit, donde cada átomo tiene un color proporcional a su importancia.

---

## 4. Validación química de las explicaciones

### El problema
Que el modelo señale un átomo como "importante" no significa que sea correcto. Necesitamos verificar que los átomos señalados corresponden a **grupos funcionales con toxicidad documentada**.

### Patrones SMARTS por vía de toxicidad

Para cada tarea Tox21, definimos patrones SMARTS (un lenguaje de búsqueda de subestructuras) que representan los grupos funcionales conocidos por causar toxicidad en esa vía:

| Tarea | Grupo funcional esperado | Patrón SMARTS | Por qué es tóxico |
|---|---|---|---|
| **SR-ARE** | Fosforotioato (P=S) | `[P](=S)([O,S])([O,S])` | Genera radicales libres al metabolizarse |
| **SR-ARE** | Grupo nitro | `[N+](=O)[O-]` | Electrófilo que depleta glutatión |
| **NR-AhR** | Naftaleno | `c1ccc2ccccc2c1` | Aromático plano que encaja en el receptor |
| **NR-Aromatase** | Triazol | `n1cncn1` | Coordina con el hierro del CYP450, inhibiéndolo |
| **NR-ER** | Fenol | `c1ccc(O)cc1` | Mimetiza la estructura del estrógeno |
| **SR-p53** | Epóxido | `C1OC1` | Agente alquilante que daña el ADN |
| **SR-MMP** | Fosforotioato | `[P](=S)([O,S])([O,S])` | Despolariza la membrana mitocondrial |

### Métrica: Precision@k

```
Precision@k = (nº de moléculas donde al menos 1 de los k átomos más importantes
               pertenece a un grupo funcional tóxico conocido)
              / (total de moléculas evaluadas)
```

**Ejemplo con Clorpirifos y SR-ARE:**

```
Molécula: CCOP(=S)(OCC)Oc1cc(Cl)c(Cl)cc1Cl

Átomos por importancia (GNNExplainer):
  1. P (fósforo)     → importancia 0.95  ✓ grupo fosforotioato [P](=S)
  2. S (azufre)      → importancia 0.88  ✓ grupo fosforotioato
  3. Cl (cloro, pos 1) → importancia 0.72
  4. O (oxígeno, pos 2) → importancia 0.65
  5. C (carbono, pos 3) → importancia 0.45

Precision@1: ✓ (el átomo #1, P, pertenece al grupo fosforotioato)
Precision@3: ✓ (al menos 1 de los top-3 pertenece al grupo)
```

### Fidelidad del subgrafo

Otra métrica: si solo mantenemos los 5 átomos más importantes y borramos el resto, ¿la predicción se mantiene?

```
Fidelidad = AUC(modelo con subgrafo top-5) / AUC(modelo con grafo completo)
Objetivo: fidelidad > 0.95 (la predicción depende realmente de esos átomos)
```

### Coherencia entre métodos

Si GNNExplainer y Grad-CAM señalan los **mismos átomos** como importantes, la explicación es más confiable:

```
Coherencia = correlación de Spearman entre rankings de importancia
Objetivo: > 0.70
```

---

## 5. Objetivos de la Fase IV

| Métrica | Objetivo |
|---|---|
| Precision@1 (GNNExplainer) | > 65% |
| Precision@3 (GNNExplainer) | > 80% |
| Precision@1 (Grad-CAM) | > 55% |
| Precision@3 (Grad-CAM) | > 70% |
| Fidelidad del subgrafo top-5 | Diferencia < 0.05 AUC |
| Coherencia GNNExp vs GradCAM | Spearman > 0.70 |

---

## 6. Casos de estudio detallados

Para al menos 3 moléculas del corpus panameño, documentar:

1. **Molécula**: nombre, SMILES, familia química
2. **Predicción**: probabilidades en las 12 tareas, tarea con mayor riesgo
3. **Explicación GNNExplainer**: imagen SVG, top-5 átomos, grupos funcionales
4. **Explicación Grad-CAM**: imagen SVG, top-5 átomos, comparación con GNNExplainer
5. **Validación química**: ¿los átomos señalados corresponden al mecanismo documentado?
6. **Comparación con GHS**: ¿la predicción es coherente con las etiquetas de peligro regulatorias?

---

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/xai/gnn_explainer.py` | GNNExplainer con _SingleTaskWrapper |
| `src/xai/grad_cam.py` | Grad-CAM adaptado a grafos |
| `src/xai/visualizer.py` | Dibuja moléculas SVG coloreadas por importancia |
| `src/evaluation/chemical_coherence.py` | Patrones SMARTS + Precision@k |
