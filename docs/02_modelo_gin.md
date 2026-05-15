# Modelo GNN-GIN

**Módulo:** `src/models/gin.py`  
**Fase:** III — Modelo GNN-GIN (Semanas 5–6)

---

## Descripción

Implementa **GINToxicity**, una Graph Isomorphism Network (GIN) para predicción multitarea de toxicidad sobre las 12 dianas biológicas del benchmark Tox21. Opera sobre grafos moleculares donde los átomos son nodos y los enlaces son aristas.

**¿Por qué GIN y no GCN o SMILES?**

```
Descriptores moleculares  → requieren ingeniería de features manual
                             XAI sobre descriptores ≠ XAI sobre átomos

SMILES como texto         → pierde información topológica
                             el mismo átomo puede estar en posiciones distintas

GCN                       → usa media ponderada — no preserva multiplicidad
                             menos expresivo que GIN en jerarquía 1-WL

GIN (este proyecto)       → representación nativa de la molécula
                             invariante a permutaciones de átomos
                             XAI directamente sobre átomos del grafo
                             máximamente expresivo entre GNNs de 1er orden
```

---

## Arquitectura

```
Input: grafo molecular G = (V, E)
  V = átomos (feature dim: 45)
  E = enlaces (feature dim: 9)
           │
┌──────────▼──────────────────────────────────────────────┐
│  BLOQUE 1 — Embedding inicial                           │
│  Linear(45 → d) → BatchNorm1d(d) → ReLU                │
│  d = 128 (base) / 256 (variante grande)                 │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  BLOQUE 2 — Message Passing GIN  (L = 3 a 5 capas)     │
│                                                         │
│  Para cada capa l:                                      │
│    h_v^(l) = MLP( (1+ε)·h_v^(l-1) + Σ_{u∈N(v)} h_u )  │
│    → BatchNorm1d → ReLU → Dropout(0.3)                  │
│    → h_v^(l) = h_v^(l) + h_v^(l-1)  ← residual        │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  BLOQUE 3 — Readout global                              │
│  h_G = CONCAT( mean_pool({h_v}), max_pool({h_v}) )     │
│  dim(h_G) = 2d                                          │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  BLOQUE 4 — Clasificador multitarea                     │
│  Linear(2d→d) → BN → ReLU → Dropout                    │
│  Linear(d→d/2) → BN → ReLU → Dropout                   │
│  Linear(d/2→12) → (Sigmoid en evaluación)              │
└──────────┬──────────────────────────────────────────────┘
           │
Output: [P(NR-AR), P(NR-AhR), ..., P(SR-p53)]
         12 probabilidades — una por diana biológica
```

---

## Capa GINLayer

```python
class GINLayer(nn.Module):
    # h_v^(l) = MLP( (1+ε)·h_v^(l-1) + Σ h_u^(l-1) )
    # MLP interno: Linear → BN → ReLU → Linear → BN
    # + conexión residual (proyección lineal si cambia dimensión)
    # + Dropout(0.3-0.5)
```

El parámetro `ε` es **entrenable** (`train_eps=True`), lo que permite al modelo ajustar el peso de la auto-información del nodo.

---

## Dianas biológicas Tox21 (12 tareas)

| ID | Diana | Sistema afectado | Relevancia en agroquímicos |
|---|---|---|---|
| NR-AR | Receptor de andrógenos | Endocrino — reproducción | Triazinas, fungicidas azólicos |
| NR-AR-LBD | Dominio ligando AR | Endocrino — reproducción | Triazinas, fungicidas azólicos |
| NR-AhR | Receptor aril-hidrocarburo | Hígado, inmunidad | Organoclorados, dioxinas |
| NR-Aromatase | Aromatasa (CYP19) | Endocrino — estrógenos | Fungicidas azólicos (inhibición CYP) |
| NR-ER | Receptor de estrógenos | Endocrino — reproducción | Organofosforados, carbamatos |
| NR-ER-LBD | Dominio ligando ER | Endocrino — reproducción | Organofosforados, carbamatos |
| NR-PPAR-gamma | Receptor PPAR-γ | Metabolismo lipídico | Herbicidas, fungicidas |
| SR-ARE | Estrés oxidativo (Nrf2/ARE) | Hígado, riñón, SNC | Organofosforados, glifosato |
| SR-AtAD5 | Daño al ADN — mitocondria | Genotoxicidad | Fungicidas, insecticidas |
| SR-HSE | Estrés por calor | Proteotoxicidad celular | Piretroides, organofosforados |
| SR-MMP | Potencial membrana mitocondrial | Hígado, corazón, músculo | Insecticidas generales |
| SR-p53 | Vía p53 — daño al ADN | Genotoxicidad, carcinogénesis | Fungicidas, herbicidas |

---

## Hiperparámetros

```yaml
# config/config.yaml
model:
  node_feat_dim: 45
  hidden_dim:    128     # variante grande: 256
  n_layers:      3       # variante profunda: 4 o 5
  n_tasks:       12
  dropout:       0.3
```

### Ablation study recomendado

| Configuración | hidden_dim | n_layers | Params aprox |
|---|---|---|---|
| Base | 128 | 3 | ~500K |
| Grande | 256 | 3 | ~1.8M |
| Profunda | 128 | 5 | ~800K |
| Grande+profunda | 256 | 5 | ~3.1M |

---

## Instanciación y forward pass

```python
from src.models.gin import GINToxicity

model = GINToxicity(
    node_feat_dim=45,
    hidden_dim=128,
    n_layers=3,
    n_tasks=12,
    dropout=0.3
)

# Forward pass (PyG batch)
logits = model(batch.x, batch.edge_index, batch.batch)
# logits: (batch_size, 12) — sin activar
probs  = torch.sigmoid(logits)
# probs:  (batch_size, 12) — probabilidades [0,1]
```

---

## Referencia de rendimiento en Tox21

```
Random Forest + Morgan ECFP4  →  AUC ~0.77
MLP + Morgan ECFP4            →  AUC ~0.79
SMILES2vec (CNN-GRU)          →  AUC ~0.81
GCN                           →  AUC ~0.83
GIN (este proyecto — objetivo)→  AUC > 0.83
Attentive FP (ref. alta)      →  AUC ~0.85
```

---

## Guardado del modelo

```python
torch.save(model.state_dict(), "outputs/models/best_gin_model.pt")

# Carga
model = GINToxicity(...)
model.load_state_dict(torch.load("outputs/models/best_gin_model.pt"))
model.eval()
```

---

## Entregables

- [ ] `src/models/gin.py` implementado y testeado (forward pass sin errores)
- [ ] Forward pass verificado con batch sintético de 4 moléculas
- [ ] Convergencia verificada en un solo fold antes del 5-fold CV completo
- [ ] Ablation study: d=128 vs d=256, 3 vs 5 capas documentado
- [ ] AUC promedio ≥ 0.82 en test scaffold split

---

## Dependencias

```
torch>=2.0
torch_geometric>=2.4   # GINConv, global_mean_pool, global_max_pool
```
