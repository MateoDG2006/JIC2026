# Pipeline de Datos

**Módulos:** `src/data/featurizer.py`, `src/data/dataset.py`, `src/data/splitter.py`, `src/data/pubchem_api.py`  
**Fase:** I — Fundamentos y datos (Semanas 1–2)

---

## Descripción

El pipeline transforma SMILES crudos en grafos moleculares listos para PyTorch Geometric. Incluye dos flujos paralelos: descarga del dataset de entrenamiento Tox21 (vía DeepChem) y construcción del corpus panameño de plaguicidas (vía PubChem API).

---

## Flujo general

```
PubChem API          DeepChem/MoleculeNet
(corpus panameño)    (Tox21 entrenamiento)
        │                    │
        ▼                    ▼
  SMILES + CID        SMILES + labels (12 tareas)
        │                    │
        └──────────┬──────────┘
                   ▼
         featurizer.py
         SMILES → grafo molecular
         (RDKit → PyG Data)
                   │
                   ▼
         splitter.py
         Scaffold split (Murcko)
         70% train / 15% val / 15% test
                   │
                   ▼
         dataset.py
         ToxicityDataset (PyG)
         data/processed/graphs_*.pt
```

---

## 1. Construcción del grafo molecular (`featurizer.py`)

### Features de nodo (átomo) — dim ~45

| Feature | Codificación | Dim |
|---|---|---|
| Tipo de átomo | one-hot: C,N,O,F,P,S,Cl,Br,I,other | 10 |
| Grado (# vecinos) | one-hot: 0–10 | 11 |
| Hibridización | one-hot: SP,SP2,SP3,SP3D,SP3D2 | 5 |
| Aromaticidad | binario | 1 |
| Hidrógenos totales | one-hot: 0–4 | 5 |
| Carga formal | one-hot: -2,-1,0,1,2 | 5 |
| En anillo | binario | 1 |
| Tamaño de anillo | one-hot por tamaño | 6 |

### Features de arista (enlace) — dim ~9

| Feature | Codificación | Dim |
|---|---|---|
| Tipo de enlace | one-hot: SINGLE,DOUBLE,TRIPLE,AROMATIC | 4 |
| Conjugado | binario | 1 |
| En anillo | binario | 1 |
| Estereo | one-hot: NONE,E,Z | 3 |

### Objeto Data (PyTorch Geometric)

```python
data = Data(
    x          = tensor([num_atoms, 45]),     # features de nodo
    edge_index = tensor([2, num_edges*2]),    # aristas bidireccionales
    edge_attr  = tensor([num_edges*2, 9]),    # features de arista
    y          = tensor([12]),                # etiquetas Tox21
    mask       = tensor([12], dtype=bool),   # True donde hay medición
)
```

---

## 2. Scaffold Split (`splitter.py`)

Divide el dataset por **scaffold de Murcko**: moléculas con el mismo scaffold central van siempre al mismo conjunto. Esto evalúa generalización real a nuevas familias moleculares.

```
División:  70% train  /  15% val  /  15% test
           (por scaffold, no aleatorio)
```

Los índices se guardan en `data/splits/scaffold_split_indices.json` para reproducibilidad.

---

## 3. Dataset PyG (`dataset.py`)

```python
from src.data.dataset import ToxicityDataset

train_ds = ToxicityDataset(root="data/processed", split="train")
val_ds   = ToxicityDataset(root="data/processed", split="val")
test_ds  = ToxicityDataset(root="data/processed", split="test")

loader = DataLoader(train_ds, batch_size=32, shuffle=True)
```

Cada batch agrega grafos de distintas moléculas en un super-grafo:

```
batch.x          → (total_atoms_en_batch, 45)
batch.edge_index → (2, total_edges_en_batch)
batch.batch      → (total_atoms,) índice de molécula por átomo
batch.y          → (batch_size, 12)
batch.mask       → (batch_size, 12)
```

---

## 4. Fuentes de datos

### 4a. Tox21 vía DeepChem (entrenamiento)

```python
import deepchem as dc

tasks, datasets, transformers = dc.molnet.load_tox21(
    featurizer=dc.feat.MolGraphConvFeaturizer(use_edges=True),
    splitter='scaffold'
)
train, val, test = datasets
```

### 4b. Corpus panameño vía PubChem API (`pubchem_api.py`)

Pipeline de 3 pasos para construir el corpus con trazabilidad verificable:

**Paso 1 — Classification HID 72** (árbol de plaguicidas PubChem):

```
Familias cubiertas: Organophosphates, Carbamates, Triazines,
                    Azole_fungicides, Pyrethroids, Herbicides
Endpoint: /pug/classification/hid/{hid}/cids/JSON
```

**Paso 2 — PubChem Compound** (SMILES canónicos por CID):

```
Endpoint: /pug/compound/cid/{cids}/property/CanonicalSMILES/JSON
Lotes de 100 CIDs, rate limit: 0.4s entre requests
```

**Paso 3 — PubChem Hazard GHS** (etiquetas regulatorias, solo validación externa):

```
Codes relevantes: H300-H302 (toxicidad oral), H360-H361 (reproductivo)
                  H340/H350 (genotóxico/carcinógeno), H400-H412 (acuático)
Endpoint: /pug/compound/cid/{cid}/JSON → sección Safety and Hazards
```

#### Ingredientes activos MIDA incluidos

```
Organofosforados: Clorpirifos, Malatión, Dimetoato, Metil paratión
Carbamatos:       Carbaryl, Metomilo, Aldicarb
Triazinas:        Atrazina, Simazina
Fungicidas azol:  Tebuconazol, Propiconazol, Difenoconazol
Piretroides:      Cipermetrina, Deltametrina, Lambda-cihalotrina
Herbicidas:       Glifosato, Paraquat, 2,4-D, Mancozeb, Clorotalonil
```

---

## 5. Máscara NaN (`loss.py`)

Tox21 tiene datos faltantes por tarea. La `MaskedBCELoss` solo calcula pérdida donde hay medición:

```python
loss_per_entry = BCE(logits, targets)   # (batch, 12)
masked_loss    = loss_per_entry * mask  # cero donde NaN
final_loss     = masked_loss.sum() / mask.sum()
```

---

## Archivos generados

```
data/raw/
├── pubchem_tox21_aids.csv        # 12 ensayos desde PubChem BioAssay
├── pubchem_panama_cids.csv       # corpus panameño con SMILES
└── pubchem_ghs_labels.csv        # etiquetas GHS para validación externa

data/processed/
├── graphs_train.pt               # grafos moleculares — entrenamiento
├── graphs_val.pt                 # grafos moleculares — validación
├── graphs_test.pt                # grafos moleculares — prueba
└── panama_corpus.pt              # corpus panameño procesado

data/splits/
└── scaffold_split_indices.json   # índices reproducibles
```

---

## Entregables

- [ ] Entorno instalado (`rdkit`, `torch_geometric`, `deepchem`, `wandb`)
- [ ] `graphs_train.pt`, `graphs_val.pt`, `graphs_test.pt` generados
- [ ] `panama_corpus.pt` con 30+ plaguicidas panameños verificados
- [ ] `MaskedBCELoss` testeada unitariamente
- [ ] Distribución de clases y NaN por tarea documentada en `notebooks/01_data_exploration.ipynb`
- [ ] Scaffold split verificado (sin scaffolds compartidos entre conjuntos)

---

## Dependencias

```
rdkit>=2023.09
torch>=2.0
torch_geometric>=2.4
deepchem>=2.7
pandas, numpy, requests
```
