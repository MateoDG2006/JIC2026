# CLAUDE.md — Predicción de Toxicidad de Agroquímicos con GNN + XAI

## Descripción del Proyecto

Sistema de **química computacional** basado en Graph Neural Networks (arquitectura GIN) para predecir el perfil de toxicidad de plaguicidas usados en la agricultura de exportación panameña. El sistema incorpora técnicas de **Explainable AI** (GNNExplainer y Grad-CAM) para identificar qué grupos funcionales de cada molécula son responsables de la toxicidad predicha.

El modelo opera directamente sobre **grafos moleculares** — átomos como nodos, enlaces como aristas — sin necesidad de descriptores moleculares calculados manualmente. Entrenado sobre Tox21 (12 tareas de toxicidad), evaluado específicamente sobre compuestos registrados en el MIDA de Panamá.

---

## Hipótesis de investigación

> Una GNN-GIN entrenada sobre grafos moleculares del dataset Tox21 predice el perfil de toxicidad multitarea de plaguicidas agrícolas panameños con AUC-ROC superior a modelos QSAR clásicos, y las explicaciones XAI identifican grupos funcionales químicamente coherentes con los mecanismos de toxicidad documentados en la literatura.

---

## Objetivos

### General
Desarrollar, entrenar y validar un sistema de química computacional GNN-GIN + XAI para predicción de toxicidad de agroquímicos, orientado a apoyar la evaluación regulatoria del MIDA y el MINSA en Panamá.

### Específicos
1. Implementar pipeline de conversión SMILES → grafo molecular con RDKit y PyTorch Geometric
2. Construir corpus de plaguicidas registrados en Panamá con datos de toxicidad Tox21/ToxCast
3. Entrenar modelo GNN-GIN multitarea con 12 salidas (dianas biológicas Tox21)
4. Comparar contra 3 baselines bajo 5-fold CV con scaffold split
5. Aplicar GNNExplainer y Grad-CAM para identificar grupos funcionales tóxicos
6. Validar químicamente las explicaciones XAI contra mecanismos documentados
7. Generar reportes interpretados para actores institucionales (MIDA, MINSA)

---

## Estructura del repositorio

```
gnn-toxicity-panama/
│
├── CLAUDE.md                          # Este archivo — planificación y contexto del proyecto
│
├── data/
│   ├── raw/
│   │   ├── tox21.csv                          # Dataset Tox21 — MoleculeNet (entrenamiento)
│   │   ├── toxcast.csv                        # Dataset ToxCast — EPA (fase avanzada)
│   │   ├── pubchem_tox21_aids.csv             # AIDs Tox21 desde PubChem BioAssay
│   │   ├── pubchem_panama_cids.csv            # CIDs plaguicidas panameños desde PubChem
│   │   ├── pubchem_classification_hid72.json  # Árbol Pesticides HID 72
│   │   ├── pubchem_ghs_labels.csv             # Etiquetas GHS por CID — validación externa
│   │   └── ppdb_pesticides.csv                # Datos experimentales PPDB
│   ├── processed/
│   │   ├── graphs_train.pt            # Grafos moleculares — entrenamiento
│   │   ├── graphs_val.pt              # Grafos moleculares — validación
│   │   ├── graphs_test.pt             # Grafos moleculares — prueba
│   │   └── panama_corpus.pt           # Corpus panameño — construido desde PubChem
│   └── splits/
│       └── scaffold_split_indices.json
│
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── pubchem_api.py             # Cliente PubChem: Classification/Compound/BioAssay/GHS
│   │   ├── featurizer.py              # SMILES → grafo molecular (RDKit)
│   │   ├── dataset.py                 # ToxicityDataset (PyG Dataset)
│   │   └── splitter.py                # Scaffold split con DeepChem
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gin.py                     # Arquitectura GNN-GIN completa
│   │   ├── baselines.py               # RF + MLP + SMILES2vec
│   │   └── readout.py                 # Global mean+max pooling
│   │
│   ├── training/
│   │   ├── __init__.py
│   │   ├── trainer.py                 # Loop de entrenamiento con early stopping
│   │   ├── loss.py                    # BCEWithLogitsLoss con máscara NaN
│   │   └── metrics.py                 # AUC-ROC por tarea y promedio
│   │
│   ├── xai/
│   │   ├── __init__.py
│   │   ├── gnn_explainer.py           # GNNExplainer sobre modelo entrenado
│   │   ├── grad_cam.py                # Grad-CAM adaptado a grafos
│   │   └── visualizer.py             # Render de moléculas con importancia XAI
│   │
│   └── evaluation/
│       ├── __init__.py
│       ├── cross_validation.py        # 5-fold CV con scaffold split
│       └── chemical_coherence.py      # Validación química de explicaciones XAI
│
├── notebooks/
│   ├── 00_pubchem_data_pipeline.ipynb  # PubChem API: HID72, BioAssay, Compound, GHS
│   ├── 01_data_exploration.ipynb      # EDA: distribución de clases, NaN, scaffolds
│   ├── 02_graph_construction.ipynb    # Visualización de grafos moleculares
│   ├── 03_baseline_models.ipynb       # Entrenamiento y evaluación de baselines
│   ├── 04_gnn_training.ipynb          # Entrenamiento GNN-GIN
│   ├── 05_xai_analysis.ipynb          # Análisis XAI: GNNExplainer + Grad-CAM
│   ├── 06_panama_application.ipynb    # Aplicación a plaguicidas panameños
│   └── 07_ghs_validation.ipynb        # Validación externa: predicciones vs etiquetas GHS
│
├── outputs/
│   ├── models/
│   │   └── best_gin_model.pt          # Mejor modelo guardado (early stopping)
│   ├── results/
│   │   ├── baseline_results.csv       # AUC por tarea — baselines
│   │   ├── gin_results.csv            # AUC por tarea — GNN-GIN
│   │   └── cv_summary.csv             # Resumen 5-fold CV
│   ├── xai/
│   │   ├── explanations/              # Máscaras GNNExplainer por molécula
│   │   └── figures/                   # Imágenes de moléculas coloreadas por XAI
│   └── reports/
│       ├── report_mida_minsa.pdf      # Reporte para MIDA/MINSA
│       └── panama_pesticides_profile.csv
│
├── config/
│   └── config.yaml                    # Todos los hiperparámetros del proyecto
│
├── requirements.txt
├── environment.yml
└── README.md
```

---

## Arquitectura del modelo GNN-GIN

```
Input: SMILES string
        ↓
[ RDKit: SMILES → Molecular Graph ]
  - Nodes: atoms  (feature dim: ~39)
  - Edges: bonds  (feature dim:   9)
        ↓
┌─────────────────────────────────────────────────────────────────────┐
│  BLOQUE 1 — Embedding inicial                                       │
│                                                                     │
│  Linear(39 → d)  →  BatchNorm1d(d)  →  ReLU                        │
│  d = 128 (base) / 256 (variante)                                    │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│  BLOQUE 2 — Message Passing GIN  (L = 3 a 5 capas)                 │
│                                                                     │
│  Para cada capa l:                                                  │
│    h_v^(l) = MLP( (1 + ε) · h_v^(l-1)  +  Σ h_u^(l-1) )          │
│           ↓                                                         │
│    BatchNorm1d  →  ReLU  →  Dropout(0.3-0.5)                       │
│           ↓                                                         │
│    h_v^(l) = h_v^(l) + h_v^(l-1)   ← conexión residual            │
│                                                                     │
│  Repite L veces                                                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│  BLOQUE 3 — Readout global                                          │
│                                                                     │
│  h_G = CONCAT( mean_pool({h_v}),  max_pool({h_v}) )                │
│  dim(h_G) = 2d                                                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│  BLOQUE 4 — Clasificador multitarea                                 │
│                                                                     │
│  Linear(2d → d)   →  BatchNorm  →  ReLU  →  Dropout               │
│  Linear(d → d/2)  →  BatchNorm  →  ReLU  →  Dropout               │
│  Linear(d/2 → 12) →  Sigmoid                                       │
│                                                                     │
│  Salida: 12 probabilidades ∈ [0,1] — una por diana biológica       │
└─────────────────────────────────────────────────────────────────────┘
        ↓
Output: [P(NR-AR), P(NR-AhR), P(NR-ER), ..., P(SR-p53)]
         probabilidad de toxicidad por cada una de las 12 vías Tox21
```

### Dianas biológicas Tox21 (12 tareas)

| ID | Diana | Sistema afectado | Relevancia en agroquímicos |
|---|---|---|---|
| NR-AR | Receptor de andrógenos | Endocrino — reproducción | Triazinas, fungicidas azólicos |
| NR-AR-LBD | Dominio ligando AR | Endocrino — reproducción | Triazinas, fungicidas azólicos |
| NR-AhR | Receptor aril-hidrocarburo | Hígado, inmunidad | Organoclorados, dioxinas |
| NR-Aromatase | Aromatasa (CYP19) | Endocrino — estrógenos | Fungicidas azólicos (inhibición CYP) |
| NR-ER | Receptor de estrógenos | Endocrino — reproducción | Organofosforados, carbamatos |
| NR-ER-LBD | Dominio ligando ER | Endocrino — reproducción | Organofosforados, carbamatos |
| NR-PPAR-gamma | Receptor PPAR-γ | Metabolismo lipídico, hígado | Herbicidas, fungicidas |
| SR-ARE | Estrés oxidativo (Nrf2/ARE) | Hígado, riñón, SNC | Organofosforados, glifosato |
| SR-AtAD5 | Daño al ADN — mitocondria | Genotoxicidad | Fungicidas, insecticidas |
| SR-HSE | Estrés por calor (proteínas) | Proteotoxicidad celular | Piretroides, organofosforados |
| SR-MMP | Potencial membrana mitocondrial | Hígado, corazón, músculo | Insecticidas generales |
| SR-p53 | Vía p53 — daño al ADN | Genotoxicidad, carcinogénesis | Fungicidas, herbicidas |

---

## Fase I — Fundamentos y datos

**Duración estimada:** 2 semanas  
**Objetivo:** Pipeline de datos funcional y corpus molecular panameño validado

### Tareas

#### 1.1 Configuración del entorno

```bash
# Crear entorno conda
conda create -n toxgnn python=3.10
conda activate toxgnn

# Química computacional
conda install -c conda-forge rdkit

# Deep learning y GNN
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install torch_geometric
pip install torch_scatter torch_sparse torch_cluster -f https://data.pyg.org/whl/torch-2.0.0+cu118.html

# Datasets y utilidades
pip install deepchem wandb captum pandas scikit-learn matplotlib seaborn

# Verificar instalación
python -c "import rdkit; import torch_geometric; import deepchem; print('OK')"
```

#### 1.2 Descarga de datos

Hay dos fuentes de datos paralelas: **MoleculeNet/DeepChem** para el entrenamiento del modelo,
y **PubChem API** para construir el corpus panameño con trazabilidad verificable.

##### 1.2a — Tox21 vía DeepChem (entrenamiento principal)

```python
# src/data/download.py
import deepchem as dc

# Tox21 — dataset principal de entrenamiento
tasks, datasets, transformers = dc.molnet.load_tox21(
    featurizer=dc.feat.MolGraphConvFeaturizer(use_edges=True),
    splitter='scaffold'
)
train, val, test = datasets

# ToxCast — fase avanzada (mayor volumen, más ruido)
tasks_tc, datasets_tc, _ = dc.molnet.load_toxcast(
    featurizer=dc.feat.MolGraphConvFeaturizer(use_edges=True),
    splitter='scaffold'
)
```

##### 1.2b — Tox21 vía PubChem BioAssay (trazabilidad y validación)

Los 12 ensayos de Tox21 tienen AIDs publicados en PubChem BioAssay.
Descargarlos directamente permite citar la fuente primaria del NIH en el proyecto.

```python
# src/data/pubchem_api.py  — sección BioAssay

import requests
import pandas as pd
import time

# AIDs oficiales de los 12 ensayos Tox21 en PubChem BioAssay
TOX21_AIDS = {
    'NR-AR':       720637,
    'NR-AR-LBD':   743035,
    'NR-AhR':      743122,
    'NR-Aromatase':743139,
    'NR-ER':       743040,
    'NR-ER-LBD':   743042,
    'NR-PPAR-g':   743140,
    'SR-ARE':      743219,
    'SR-AtAD5':    743221,
    'SR-HSE':      743226,
    'SR-MMP':      743240,
    'SR-p53':      743241,
}

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

def fetch_bioassay_data(aid: int, task_name: str) -> pd.DataFrame:
    """
    Descarga resultados de un ensayo PubChem BioAssay.
    Retorna DataFrame con columnas: CID, SMILES, activity (1=Active, 0=Inactive)
    """
    url = f"{BASE}/bioassay/AID/{aid}/CSV"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    from io import StringIO
    df = pd.read_csv(StringIO(resp.text))

    # Normalizar columnas clave
    df = df.rename(columns={
        'PUBCHEM_CID': 'CID',
        'PUBCHEM_ACTIVITY_OUTCOME': 'activity_raw'
    })
    df['activity'] = df['activity_raw'].map({'Active': 1, 'Inactive': 0})
    df['task']     = task_name
    df['AID']      = aid

    return df[['CID', 'task', 'AID', 'activity']].dropna()


def build_tox21_from_pubchem(output_path: str = "data/raw/pubchem_tox21_aids.csv"):
    """Descarga y concatena los 12 ensayos Tox21 desde PubChem BioAssay."""
    all_dfs = []
    for task, aid in TOX21_AIDS.items():
        print(f"  Descargando {task} (AID {aid})...")
        df = fetch_bioassay_data(aid, task)
        all_dfs.append(df)
        time.sleep(0.4)          # respetar rate limit de PubChem API

    result = pd.concat(all_dfs, ignore_index=True)
    result.to_csv(output_path, index=False)
    print(f"Guardado: {output_path}  ({len(result)} registros)")
    return result
```


#### 1.3 Construcción del grafo molecular

```python
# src/data/featurizer.py
from rdkit import Chem
from rdkit.Chem import AllChem
import torch
from torch_geometric.data import Data

# Diccionarios de características
ATOM_TYPES    = ['C','N','O','F','P','S','Cl','Br','I','other']
HYBRIDIZATION = [Chem.rdchem.HybridizationType.SP,
                 Chem.rdchem.HybridizationType.SP2,
                 Chem.rdchem.HybridizationType.SP3,
                 Chem.rdchem.HybridizationType.SP3D,
                 Chem.rdchem.HybridizationType.SP3D2]
BOND_TYPES    = [Chem.rdchem.BondType.SINGLE,
                 Chem.rdchem.BondType.DOUBLE,
                 Chem.rdchem.BondType.TRIPLE,
                 Chem.rdchem.BondType.AROMATIC]

def atom_features(atom) -> list:
    """Vector de características de un átomo — dim total: ~39"""
    return (
        one_hot(atom.GetSymbol(), ATOM_TYPES)              +  # 10
        one_hot(atom.GetDegree(), list(range(11)))          +  # 11
        one_hot(atom.GetHybridization(), HYBRIDIZATION)    +  #  6
        [int(atom.GetIsAromatic())]                         +  #  1
        one_hot(atom.GetTotalNumHs(), [0,1,2,3,4])         +  #  5
        one_hot(atom.GetFormalCharge(), [-2,-1,0,1,2])     +  #  5
        [int(atom.IsInRing())]                              +  #  1
        ring_size_features(atom)                               #  6 → total ~45
    )

def bond_features(bond) -> list:
    """Vector de características de un enlace — dim total: ~9"""
    return (
        one_hot(bond.GetBondType(), BOND_TYPES)            +  # 4
        [int(bond.GetIsConjugated())]                      +  # 1
        [int(bond.IsInRing())]                             +  # 1
        one_hot(bond.GetStereo(), [                            # 3
            Chem.rdchem.BondStereo.STEREONONE,
            Chem.rdchem.BondStereo.STEREOE,
            Chem.rdchem.BondStereo.STEREOZ
        ])
    )

def smiles_to_graph(smiles: str, labels=None, mask=None) -> Data | None:
    """
    Convierte un SMILES en un objeto Data de PyTorch Geometric.
    Retorna None si el SMILES es inválido.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Canonicalizar
    smiles_canon = Chem.MolToSmiles(mol)
    mol = Chem.MolFromSmiles(smiles_canon)

    # Nodos
    x = torch.tensor([atom_features(a) for a in mol.GetAtoms()],
                     dtype=torch.float)

    # Aristas (bidireccional)
    edge_index, edge_attr = [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        feat = bond_features(bond)
        edge_index += [[i, j], [j, i]]
        edge_attr  += [feat, feat]

    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
    edge_attr  = torch.tensor(edge_attr,  dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

    if labels is not None:
        data.y    = torch.tensor(labels, dtype=torch.float)
        data.mask = torch.tensor(mask,   dtype=torch.bool)

    return data
```

#### 1.4 Scaffold split

```python
# src/data/splitter.py
from rdkit.Chem.Scaffolds import MurckoScaffold
from collections import defaultdict
import numpy as np

def scaffold_split(smiles_list, frac_train=0.7, frac_val=0.15, frac_test=0.15):
    """
    Divide el dataset por scaffold de Murcko.
    Moléculas con el mismo scaffold van siempre al mismo conjunto.
    """
    scaffolds = defaultdict(list)

    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(
            mol=mol, includeChirality=False
        )
        scaffolds[scaffold].append(i)

    # Ordenar scaffolds por tamaño (descendente) para distribución balanceada
    scaffold_sets = sorted(scaffolds.values(), key=len, reverse=True)

    n = len(smiles_list)
    train_idx, val_idx, test_idx = [], [], []

    for s in scaffold_sets:
        if len(train_idx) / n < frac_train:
            train_idx += s
        elif len(val_idx) / n < frac_val:
            val_idx += s
        else:
            test_idx += s

    return train_idx, val_idx, test_idx
```

#### 1.5 Máscara NaN

```python
# src/training/loss.py
import torch
import torch.nn as nn

class MaskedBCELoss(nn.Module):
    """
    Binary Cross Entropy con máscara para datos faltantes (NaN).
    Solo calcula la pérdida sobre las entradas con medición disponible.
    """
    def __init__(self):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss(reduction='none')

    def forward(self, logits, targets, mask):
        """
        logits:  (batch_size, 12) — salidas sin activar del modelo
        targets: (batch_size, 12) — etiquetas 0/1
        mask:    (batch_size, 12) — 1 si medición existe, 0 si NaN
        """
        loss_per_entry = self.bce(logits, targets)   # (batch, 12)
        masked_loss    = loss_per_entry * mask        # cero donde NaN
        return masked_loss.sum() / mask.sum()         # media solo sobre válidos
```

#### 1.6 Construcción del corpus panameño vía PubChem API

El corpus se construye en tres pasos usando las tres fuentes de PubChem de forma encadenada.
Esto reemplaza el diccionario manual de SMILES y garantiza trazabilidad completa a la fuente primaria.

```python
# src/data/pubchem_api.py  — sección Classification + Compound + GHS

import requests, time, json
import pandas as pd
from rdkit import Chem

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# ── PASO 1: PubChem Classification (HID 72) ─────────────────────────────────
# Descarga todos los CIDs del árbol "Pesticides" y sus subnodos por familia.

FAMILY_HIDS = {
    'Organophosphates':  73,    # subnodo de HID 72
    'Carbamates':        78,
    'Triazines':        126,
    'Azole_fungicides': 103,
    'Pyrethroids':      112,
    'Herbicides':        90,
}

def fetch_classification_cids(hid: int) -> list[int]:
    """
    Devuelve todos los CIDs bajo un nodo del árbol PubChem Classification.
    Endpoint: /pug/classification/hid/{hid}/cids/JSON
    """
    url = f"{BASE}/classification/hid/{hid}/cids/JSON"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get('IdentifierList', {}).get('CID', [])


def build_panama_cid_list(output_path: str = "data/raw/pubchem_panama_cids.csv"):
    """
    Construye la lista de CIDs de plaguicidas relevantes para Panamá
    combinando el árbol HID 72 con la lista de ingredientes activos del MIDA.
    """
    # Lista de ingredientes activos del MIDA (nombres comunes)
    MIDA_ACTIVE_INGREDIENTS = [
        'Chlorpyrifos', 'Malathion', 'Dimethoate', 'Methyl parathion',
        'Carbaryl', 'Methomyl', 'Aldicarb',
        'Atrazine', 'Simazine',
        'Tebuconazole', 'Propiconazole', 'Difenoconazole',
        'Cypermethrin', 'Deltamethrin', 'Lambda-cyhalothrin',
        'Glyphosate', 'Paraquat', '2,4-D', 'Mancozeb', 'Chlorothalonil',
    ]

    rows = []

    # Vía 1: búsqueda por nombre de ingrediente activo
    for name in MIDA_ACTIVE_INGREDIENTS:
        url = f"{BASE}/compound/name/{name}/property/CanonicalSMILES,IUPACName,MolecularFormula/JSON"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                props = resp.json()['PropertyTable']['Properties'][0]
                rows.append({
                    'name':    name,
                    'CID':     props['CID'],
                    'SMILES':  props['CanonicalSMILES'],
                    'formula': props.get('MolecularFormula', ''),
                    'source':  'MIDA_name_search',
                    'family':  'mixed',
                })
        except Exception as e:
            print(f"  No encontrado: {name} — {e}")
        time.sleep(0.35)

    # Vía 2: árbol de clasificación HID 72 → enriquecer con familias
    for family, hid in FAMILY_HIDS.items():
        cids = fetch_classification_cids(hid)[:50]   # primeros 50 por familia
        for cid in cids:
            rows.append({
                'name':    '',
                'CID':     cid,
                'SMILES':  '',
                'formula': '',
                'source':  f'classification_hid_{hid}',
                'family':  family,
            })
        time.sleep(0.5)

    df = pd.DataFrame(rows).drop_duplicates(subset='CID')
    df.to_csv(output_path, index=False)
    print(f"Corpus inicial: {len(df)} compuestos guardados en {output_path}")
    return df


# ── PASO 2: PubChem Compound — enriquecer CIDs con SMILES canónicos ─────────

def fetch_smiles_batch(cids: list[int], batch_size: int = 100) -> dict[int, str]:
    """
    Descarga SMILES canónicos para una lista de CIDs en lotes.
    Endpoint: /pug/compound/cid/{cids}/property/CanonicalSMILES/JSON
    """
    smiles_map = {}
    for i in range(0, len(cids), batch_size):
        batch  = cids[i:i+batch_size]
        cid_str = ','.join(map(str, batch))
        url     = f"{BASE}/compound/cid/{cid_str}/property/CanonicalSMILES/JSON"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            for prop in resp.json()['PropertyTable']['Properties']:
                smiles_map[prop['CID']] = prop['CanonicalSMILES']
        except Exception as e:
            print(f"  Error en batch {i//batch_size}: {e}")
        time.sleep(0.4)
    return smiles_map


def enrich_corpus_with_smiles(corpus_path: str) -> pd.DataFrame:
    """
    Completa los SMILES vacíos descargando desde PubChem Compound.
    """
    df = pd.read_csv(corpus_path)
    missing_cids = df[df['SMILES'] == '']['CID'].tolist()

    if missing_cids:
        print(f"Descargando SMILES para {len(missing_cids)} CIDs...")
        smiles_map = fetch_smiles_batch(missing_cids)
        df.loc[df['SMILES'] == '', 'SMILES'] = df['CID'].map(smiles_map)

    # Validar con RDKit y canonicalizar
    def validate_smiles(smi):
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        return Chem.MolToSmiles(mol) if mol else None

    df['SMILES_canonical'] = df['SMILES'].apply(validate_smiles)
    df = df.dropna(subset=['SMILES_canonical'])

    df.to_csv(corpus_path, index=False)
    print(f"Corpus enriquecido: {len(df)} moléculas válidas")
    return df


# ── PASO 3: PubChem Hazard (GHS) — etiquetas de validación externa ──────────

GHS_HAZARD_CODES = {
    # Toxicidad aguda
    'H300': 'fatal_oral', 'H301': 'toxic_oral', 'H302': 'harmful_oral',
    'H310': 'fatal_dermal', 'H311': 'toxic_dermal', 'H312': 'harmful_dermal',
    'H330': 'fatal_inhalation', 'H331': 'toxic_inhalation',
    # Toxicidad reproductiva y endocrina
    'H360': 'reproductive_cat1', 'H361': 'reproductive_cat2',
    'H362': 'lactation_hazard',
    # Genotoxicidad
    'H340': 'mutagenic_cat1', 'H341': 'mutagenic_cat2',
    # Carcinogenicidad
    'H350': 'carcinogenic_cat1', 'H351': 'carcinogenic_cat2',
    # Toxicidad acuática
    'H400': 'aquatic_acute_cat1', 'H410': 'aquatic_chronic_cat1',
    'H411': 'aquatic_chronic_cat2', 'H412': 'aquatic_chronic_cat3',
}

def fetch_ghs_labels(cids: list[int], output_path: str = "data/raw/pubchem_ghs_labels.csv"):
    """
    Descarga etiquetas GHS (H-statements) para cada CID.
    Usadas para VALIDACIÓN EXTERNA — no para entrenar el modelo.

    Estrategia:
        - H300/H301/H302 + H330/H331 → correlacionar con SR-ARE y SR-MMP
        - H360/H361 → correlacionar con NR-AR y NR-ER
        - H340/H350 → correlacionar con SR-p53 y SR-AtAD5
    """
    rows = []
    for cid in cids:
        url = f"{BASE}/compound/cid/{cid}/JSON"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Navegar la estructura JSON de PubChem para GHS
            sections = (data.get('Record', {})
                           .get('Section', []))
            ghs_codes = []
            for sec in sections:
                if sec.get('TOCHeading') == 'Safety and Hazards':
                    for subsec in sec.get('Section', []):
                        if 'GHS' in subsec.get('TOCHeading', ''):
                            for info in subsec.get('Information', []):
                                for val in info.get('Value', {}).get('StringWithMarkup', []):
                                    text = val.get('String', '')
                                    for code in GHS_HAZARD_CODES:
                                        if code in text:
                                            ghs_codes.append(code)

            rows.append({
                'CID':       cid,
                'ghs_codes': '|'.join(set(ghs_codes)),
                'toxic_oral':      int(any(c in ghs_codes for c in ['H300','H301','H302'])),
                'endocrine_risk':  int(any(c in ghs_codes for c in ['H360','H361'])),
                'genotoxic':       int(any(c in ghs_codes for c in ['H340','H341','H350','H351'])),
                'aquatic_tox':     int(any(c in ghs_codes for c in ['H400','H410','H411','H412'])),
            })
        except Exception as e:
            print(f"  GHS error CID {cid}: {e}")
        time.sleep(0.35)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"Etiquetas GHS guardadas: {len(df)} compuestos en {output_path}")
    return df


# ── Pipeline completo ────────────────────────────────────────────────────────

def build_full_panama_corpus():
    """
    Ejecuta el pipeline completo de 3 pasos:
      1. Classification HID 72  → lista de CIDs por familia
      2. Compound API           → SMILES canónicos verificados
      3. Hazard GHS             → etiquetas de toxicidad regulatoria

    Resultado: data/raw/pubchem_panama_cids.csv (corpus con SMILES)
               data/raw/pubchem_ghs_labels.csv  (etiquetas GHS para validación)
    """
    print("=== Paso 1: PubChem Classification (HID 72) ===")
    df = build_panama_cid_list()

    print("\n=== Paso 2: PubChem Compound (SMILES canónicos) ===")
    df = enrich_corpus_with_smiles("data/raw/pubchem_panama_cids.csv")

    print("\n=== Paso 3: PubChem Hazard GHS ===")
    cids = df['CID'].tolist()
    fetch_ghs_labels(cids)

    print("\n=== Corpus panameño completo ===")
    print(f"  Compuestos válidos: {len(df)}")
    print(f"  Familias: {df['family'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    build_full_panama_corpus()
```

### Entregables Fase I

- [ ] Entorno instalado y verificado con todas las dependencias
- [ ] `data/raw/pubchem_tox21_aids.csv` — 12 ensayos descargados desde PubChem BioAssay
- [ ] `data/raw/pubchem_panama_cids.csv` — corpus panameño con SMILES verificados desde PubChem
- [ ] `data/raw/pubchem_ghs_labels.csv` — etiquetas GHS para validación externa
- [ ] `data/processed/graphs_train.pt`, `graphs_val.pt`, `graphs_test.pt` generados
- [ ] Análisis exploratorio documentado en `notebooks/00_pubchem_data_pipeline.ipynb` y `notebooks/01_data_exploration.ipynb`
- [ ] Distribución de clases por tarea documentada (% positivos por tarea NR-AR, NR-ER, etc.)
- [ ] Distribución de NaN por tarea documentada
- [ ] Scaffold split implementado y verificado (sin scaffolds compartidos entre conjuntos)
- [ ] `data/processed/panama_corpus.pt` con 30+ plaguicidas panameños verificados en PubChem
- [ ] `MaskedBCELoss` implementada y testeada unitariamente

---

## Fase II — Baselines

**Duración estimada:** 1.5 semanas  
**Objetivo:** Tres modelos de referencia con AUC validado bajo el mismo protocolo que la GNN

> **Regla:** Si el Baseline 1 (Random Forest) no alcanza AUC ~0.77, el pipeline de datos tiene un bug. Siempre depurar los baselines antes de implementar la GNN.

### Baseline 1 — Random Forest + Fingerprints Morgan

```python
# src/models/baselines.py
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
import numpy as np

def morgan_fingerprints(smiles_list: list, radius=2, n_bits=2048) -> np.ndarray:
    """Genera fingerprints ECFP4 para una lista de SMILES."""
    fps = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        fp  = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        fps.append(list(fp))
    return np.array(fps)

class RandomForestBaseline:
    """
    Random Forest con fingerprints Morgan ECFP4.
    AUC esperado en Tox21: ~0.77
    """
    def __init__(self, n_estimators=100, n_jobs=-1):
        self.model = MultiOutputClassifier(
            RandomForestClassifier(n_estimators=n_estimators, n_jobs=n_jobs),
            n_jobs=-1
        )

    def fit(self, smiles_list, labels, mask):
        X = morgan_fingerprints(smiles_list)
        # Entrenar solo sobre tareas con suficiente cobertura
        self.model.fit(X, labels)

    def predict_proba(self, smiles_list):
        X = morgan_fingerprints(smiles_list)
        return np.array([e.predict_proba(X)[:,1]
                         for e in self.model.estimators_]).T
```

### Baseline 2 — MLP + Fingerprints Morgan

```python
class MLPBaseline(nn.Module):
    """
    MLP con fingerprints Morgan ECFP4.
    AUC esperado en Tox21: ~0.79
    """
    def __init__(self, input_dim=2048, hidden_dim=512, n_tasks=12, dropout=0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.BatchNorm1d(hidden_dim),
            nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2), nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, n_tasks)
        )

    def forward(self, x):
        return self.net(x)  # logits — aplicar Sigmoid para probabilidades
```

### Baseline 3 — SMILES2vec (CNN-GRU)

```python
class SMILES2vec(nn.Module):
    """
    Arquitectura del paper Goh et al. KDD 2018.
    AUC esperado en Tox21: ~0.81
    Entrada: secuencia SMILES codificada en one-hot (250 × vocab_size)
    """
    def __init__(self, vocab_size=60, embed_dim=50, conv_filters=192,
                 gru1_units=224, gru2_units=384, n_tasks=12, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.conv      = nn.Conv1d(embed_dim, conv_filters, kernel_size=3, padding=1)
        self.gru1      = nn.GRU(conv_filters, gru1_units,
                                batch_first=True, bidirectional=True)
        self.gru2      = nn.GRU(gru1_units * 2, gru2_units,
                                batch_first=True, bidirectional=True)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(gru2_units * 2, n_tasks)
        )

    def forward(self, x):
        # x: (batch, seq_len) — índices de caracteres SMILES
        emb  = self.embedding(x).permute(0, 2, 1)  # (batch, embed, seq)
        conv = torch.relu(self.conv(emb)).permute(0, 2, 1)
        out1, _ = self.gru1(conv)
        out2, _ = self.gru2(out1)
        return self.classifier(out2[:, -1, :])  # último estado oculto
```

### Evaluación de baselines

```python
# src/evaluation/cross_validation.py
from sklearn.metrics import roc_auc_score
import numpy as np

def evaluate_multitask_auc(y_true, y_pred, mask, task_names=None):
    """
    Calcula AUC-ROC por tarea y promedio, ignorando tareas sin medición.

    Retorna:
        auc_per_task: dict {task_name: auc_value}
        mean_auc:     float — promedio de tareas con AUC calculable
    """
    n_tasks = y_true.shape[1]
    auc_per_task = {}

    for t in range(n_tasks):
        valid   = mask[:, t].astype(bool)
        y_t     = y_true[valid, t]
        pred_t  = y_pred[valid, t]

        if len(np.unique(y_t)) < 2:
            # No hay ejemplos de ambas clases — tarea no evaluable
            continue

        name = task_names[t] if task_names else f"task_{t}"
        auc_per_task[name] = roc_auc_score(y_t, pred_t)

    mean_auc = np.mean(list(auc_per_task.values()))
    return auc_per_task, mean_auc
```

### Entregables Fase II

- [ ] Baseline 1 (RF) entrenado — AUC promedio ≥ 0.76
- [ ] Baseline 2 (MLP) entrenado — AUC promedio ≥ 0.78
- [ ] Baseline 3 (SMILES2vec) entrenado — AUC promedio ≥ 0.80
- [ ] `outputs/results/baseline_results.csv` con AUC por tarea para los tres modelos
- [ ] Curvas ROC por tarea documentadas en `notebooks/03_baseline_models.ipynb`
- [ ] Pipeline de evaluación `evaluate_multitask_auc` verificado sobre los tres baselines

---

## Fase III — Modelo GNN-GIN

**Duración estimada:** 2 semanas  
**Objetivo:** GNN-GIN entrenada con AUC > 0.82 promedio, superando los tres baselines

### Implementación del modelo

```python
# src/models/gin.py
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GINConv, global_mean_pool, global_max_pool

class GINLayer(nn.Module):
    """
    Capa GIN con MLP interno, BatchNorm, ReLU, Dropout y conexión residual.
    h_v^(l) = MLP( (1 + ε) · h_v^(l-1) + Σ h_u^(l-1) )
    """
    def __init__(self, in_dim, out_dim, dropout=0.3, eps=0.0):
        super().__init__()
        mlp = nn.Sequential(
            nn.Linear(in_dim, out_dim * 2),
            nn.BatchNorm1d(out_dim * 2),
            nn.ReLU(),
            nn.Linear(out_dim * 2, out_dim),
            nn.BatchNorm1d(out_dim),
        )
        self.conv     = GINConv(mlp, eps=eps, train_eps=True)
        self.bn       = nn.BatchNorm1d(out_dim)
        self.dropout  = nn.Dropout(dropout)
        # Proyección residual si cambia dimensión
        self.residual = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()

    def forward(self, x, edge_index):
        out = self.conv(x, edge_index)
        out = F.relu(self.bn(out))
        out = self.dropout(out)
        return out + self.residual(x)      # conexión residual


class GINToxicity(nn.Module):
    """
    GNN-GIN completa para predicción multitarea de toxicidad.

    Bloques:
        1. Embedding inicial: Linear(node_feat → d) + BN + ReLU
        2. Message Passing: L capas GINLayer con conexiones residuales
        3. Readout global: CONCAT(mean_pool, max_pool) → dim 2d
        4. Clasificador MLP: 2 capas densas + 12 salidas Sigmoid
    """
    def __init__(
        self,
        node_feat_dim: int = 45,
        hidden_dim:    int = 128,
        n_layers:      int = 3,
        n_tasks:       int = 12,
        dropout:       float = 0.3,
    ):
        super().__init__()

        # Bloque 1 — Embedding inicial
        self.input_proj = nn.Sequential(
            nn.Linear(node_feat_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )

        # Bloque 2 — Message Passing GIN
        self.gin_layers = nn.ModuleList([
            GINLayer(hidden_dim, hidden_dim, dropout=dropout)
            for _ in range(n_layers)
        ])

        # Bloque 4 — Clasificador multitarea
        # (Bloque 3 se aplica en forward con las funciones de pooling)
        readout_dim = hidden_dim * 2          # concat mean + max
        self.classifier = nn.Sequential(
            nn.Linear(readout_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, n_tasks),   # logits — Sigmoid en evaluación
        )

    def forward(self, x, edge_index, batch):
        """
        x:          (num_nodes_total, node_feat_dim)
        edge_index: (2, num_edges_total)
        batch:      (num_nodes_total,) — índice de molécula por nodo
        """
        # Bloque 1
        h = self.input_proj(x)

        # Bloque 2
        for layer in self.gin_layers:
            h = layer(h, edge_index)

        # Bloque 3 — Readout global
        h_mean = global_mean_pool(h, batch)     # (batch_size, d)
        h_max  = global_max_pool(h, batch)      # (batch_size, d)
        h_g    = torch.cat([h_mean, h_max], dim=1)  # (batch_size, 2d)

        # Bloque 4
        return self.classifier(h_g)             # (batch_size, 12) — logits
```

### Loop de entrenamiento

```python
# src/training/trainer.py
import torch
import wandb
from src.training.loss import MaskedBCELoss
from src.evaluation.cross_validation import evaluate_multitask_auc

def train_epoch(model, loader, optimizer, loss_fn, device):
    model.train()
    total_loss = 0.0

    for batch in loader:
        batch   = batch.to(device)
        logits  = model(batch.x, batch.edge_index, batch.batch)
        loss    = loss_fn(logits, batch.y, batch.mask)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item()

    return total_loss / len(loader)


def evaluate(model, loader, device, task_names=None):
    model.eval()
    all_logits, all_labels, all_masks = [], [], []

    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = model(batch.x, batch.edge_index, batch.batch)
            all_logits.append(torch.sigmoid(logits).cpu())
            all_labels.append(batch.y.cpu())
            all_masks.append(batch.mask.cpu())

    preds   = torch.cat(all_logits).numpy()
    labels  = torch.cat(all_labels).numpy()
    masks   = torch.cat(all_masks).numpy()

    return evaluate_multitask_auc(labels, preds, masks, task_names)


def train(model, train_loader, val_loader, config, device, task_names=None):
    """
    Loop principal de entrenamiento con early stopping y logging wandb.
    """
    optimizer  = torch.optim.Adam(model.parameters(), lr=config['lr'])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=20, verbose=True
    )
    loss_fn = MaskedBCELoss()

    best_val_auc = 0.0
    patience_counter = 0

    for epoch in range(config["max_epochs"]):
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, device)
        _, val_auc = evaluate(model, val_loader, device, task_names)

        scheduler.step(val_auc)

        wandb.log({
            'epoch':      epoch,
            'train_loss': train_loss,
            'val_auc':    val_auc,
            'lr':         optimizer.param_groups[0]['lr'],
        })

        if val_auc > best_val_auc:
            best_val_auc = val_auc
            patience_counter = 0
            torch.save(model.state_dict(), config['model_save_path'])
        else:
            patience_counter += 1
            if patience_counter >= config['early_stopping_patience']:
                print(f"Early stopping en época {epoch}. Mejor val_AUC: {best_val_auc:.4f}")
                break

    return best_val_auc
```

### Configuración del experimento

```yaml
# config/config.yaml
model:
  node_feat_dim: 45
  hidden_dim:    128        # probar también 256
  n_layers:      3          # probar también 4 y 5
  n_tasks:       12
  dropout:       0.3

training:
  lr:                       0.001
  batch_size:               32
  max_epochs:               250
  early_stopping_patience:  50
  grad_clip_norm:           1.0
  model_save_path:          outputs/models/best_gin_model.pt

scheduler:
  factor:    0.5
  patience:  20

evaluation:
  n_folds:   5
  split:     scaffold

wandb:
  project:   gnn-toxicity-panama
  entity:    <tu-usuario>
```

### 5-fold Cross-Validation

```python
# src/evaluation/cross_validation.py — función principal
def run_5fold_cv(smiles_list, labels_array, mask_array, model_config, train_config):
    """
    5-fold cross-validation con scaffold split.
    Retorna: DataFrame con AUC por tarea y fold, media y std.
    """
    folds   = create_scaffold_folds(smiles_list, n_folds=5)
    results = []

    for fold_idx, (train_idx, val_idx, test_idx) in enumerate(folds):
        print(f"\n=== Fold {fold_idx + 1}/5 ===")

        model = GINToxicity(**model_config).to(device)
        best_auc = train(model, ...)  # entrenamiento completo

        # Cargar mejor modelo y evaluar en test
        model.load_state_dict(torch.load(train_config['model_save_path']))
        auc_per_task, mean_auc = evaluate(model, test_loader, device, TASK_NAMES)

        results.append({'fold': fold_idx + 1, 'mean_auc': mean_auc, **auc_per_task})
        print(f"Fold {fold_idx+1} — Test AUC: {mean_auc:.4f}")

    df = pd.DataFrame(results)
    print(f"\nResultado final: {df['mean_auc'].mean():.4f} ± {df['mean_auc'].std():.4f}")
    return df
```

### Entregables Fase III

- [ ] `src/models/gin.py` implementado y testeado (forward pass sin errores)
- [ ] Convergencia verificada en un solo fold antes del CV completo
- [ ] 5-fold CV completo ejecutado — AUC ≥ 0.82 promedio
- [ ] `outputs/results/gin_results.csv` con AUC por tarea y fold
- [ ] Tabla comparativa GNN vs 3 baselines documentada
- [ ] Ablation study: d=128 vs d=256, 3 vs 5 capas GIN documentado
- [ ] Curvas de entrenamiento y convergencia en wandb

---

## Fase IV — Explainable AI

**Duración estimada:** 2 semanas  
**Objetivo:** Explicaciones XAI generadas, visualizadas y validadas químicamente

### GNNExplainer

```python
# src/xai/gnn_explainer.py
from torch_geometric.explain import Explainer, GNNExplainer as PyGExplainer

def build_explainer(model, task_index: int):
    """
    Construye un GNNExplainer para la tarea task_index.
    task_index: índice de la diana biológica (0-11 para Tox21)
    """
    explainer = Explainer(
        model=model,
        algorithm=PyGExplainer(epochs=200, lr=0.01),
        explanation_type='model',
        node_mask_type='attributes',
        edge_mask_type='object',
        model_config=dict(
            mode='binary_classification',
            task_level='graph',
            return_type='raw',           # logits
        ),
    )
    return explainer


def explain_molecule(explainer, data, task_index: int):
    """
    Genera la explicación XAI para una molécula en una tarea específica.

    Retorna:
        node_importance: tensor (num_atoms,) — importancia por átomo [0,1]
        edge_importance: tensor (num_edges,) — importancia por enlace [0,1]
    """
    explanation = explainer(
        x=data.x,
        edge_index=data.edge_index,
        batch=torch.zeros(data.x.size(0), dtype=torch.long),
        target=torch.tensor([task_index]),
    )
    return explanation.node_mask.squeeze(), explanation.edge_mask
```

### Grad-CAM para grafos

```python
# src/xai/grad_cam.py
import torch

def grad_cam_graph(model, data, task_index: int, layer_name: str = 'gin_layers'):
    """
    Calcula importancia por nodo usando Grad-CAM sobre una capa GIN específica.

    Implementación:
        alpha_k = (1/N) Σ_v [ d(y_c) / d(A_kv) ]
        Importancia(v) = ReLU( Σ_k [ alpha_k * A_kv ] )
    """
    activations = {}
    gradients   = {}

    # Hooks para capturar activaciones y gradientes
    target_layer = dict(model.named_modules())[layer_name][-1]

    def save_activation(module, input, output):
        activations['value'] = output

    def save_gradient(module, grad_input, grad_output):
        gradients['value'] = grad_output[0]

    fwd_hook = target_layer.register_forward_hook(save_activation)
    bwd_hook = target_layer.register_backward_hook(save_gradient)

    # Forward pass
    model.eval()
    logits = model(data.x, data.edge_index,
                   torch.zeros(data.x.size(0), dtype=torch.long))

    # Backward para la tarea objetivo
    model.zero_grad()
    logits[0, task_index].backward()

    fwd_hook.remove()
    bwd_hook.remove()

    # Calcular Grad-CAM
    act  = activations['value']      # (num_nodes, hidden_dim)
    grad = gradients['value']        # (num_nodes, hidden_dim)

    alpha = grad.mean(dim=0)         # (hidden_dim,) — importancia de canales
    cam   = torch.relu((act * alpha).sum(dim=1))  # (num_nodes,)

    # Normalizar a [0, 1]
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    return cam
```

### Visualización molecular

```python
# src/xai/visualizer.py
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

def draw_molecule_with_importance(smiles: str, node_importance: np.ndarray,
                                  title: str = "", save_path: str = None):
    """
    Dibuja la molécula coloreando cada átomo según su importancia XAI.
    Verde intenso = alta importancia (tóxico por este átomo)
    Blanco = baja importancia
    """
    mol = Chem.MolFromSmiles(Chem.MolToSmiles(Chem.MolFromSmiles(smiles)))

    # Normalizar importancias
    imp = np.array(node_importance)
    imp = (imp - imp.min()) / (imp.max() - imp.min() + 1e-8)

    # Colores: paleta verde para importancia alta
    colormap  = cm.get_cmap('YlOrRd')
    atom_cols = {i: colormap(float(v))[:3] for i, v in enumerate(imp)}
    bond_cols = {}

    highlight_atoms = list(range(mol.GetNumAtoms()))
    highlight_bonds = []

    drawer = rdMolDraw2D.MolDraw2DSVG(500, 400)
    drawer.drawOptions().addStereoAnnotation = False
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer, mol,
        highlightAtoms=highlight_atoms,
        highlightBonds=highlight_bonds,
        highlightAtomColors=atom_cols,
        highlightBondColors=bond_cols,
    )
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()

    if save_path:
        with open(save_path, 'w') as f:
            f.write(svg)

    return svg
```

### Validación química de las explicaciones

```python
# src/evaluation/chemical_coherence.py
"""
Valida que los átomos de alta importancia XAI corresponden a
grupos funcionales con toxicidad documentada.

Precision@k: porcentaje de moléculas donde al menos 1 de los k
átomos de mayor importancia pertenece al grupo funcional correcto.
"""

# Grupos funcionales esperados por vía Tox21
TOXIC_GROUPS = {
    'NR-AR':     ['[#6]-[#6](=O)-[#8]', '[OH]', '[NH2]'],  # ligandos AR
    'NR-ER':     ['c1ccccc1-[OH]', '[NH2]', '[OH]'],        # ligandos ER
    'SR-ARE':    ['[P](=S)', '[N+](=O)[O-]', '[Cl]', 'C=C'],# electrófilos
    'NR-AhR':   ['c1ccccc1', 'c1ccncc1', 'c1ccoc1'],        # aromáticos planos
    'SR-p53':    ['[N+](=O)[O-]', 'C=C', '[Cl]'],           # genotóxicos
    'NR-PPAR-g': ['C(=O)O', 'c1ccccc1', 'CCCC'],            # ácidos grasos
}

def precision_at_k(smiles, node_importance, task_name, k=3):
    """
    Retorna 1 si al menos uno de los k átomos más importantes
    pertenece a un grupo funcional conocido para esta vía de toxicidad.
    """
    from rdkit.Chem import MolFromSmarts, MolFromSmiles

    mol = MolFromSmiles(smiles)
    top_k_atoms = np.argsort(node_importance)[-k:]

    expected_patterns = TOXIC_GROUPS.get(task_name, [])

    for pattern in expected_patterns:
        query = MolFromSmarts(pattern)
        if query is None:
            continue
        matches = mol.GetSubstructMatches(query)
        matched_atoms = set(a for match in matches for a in match)
        if matched_atoms & set(top_k_atoms.tolist()):
            return 1
    return 0
```

### Entregables Fase IV

- [ ] GNNExplainer implementado con PyG Explainer API
- [ ] Grad-CAM implementado con hooks de activación/gradiente
- [ ] Visualizaciones generadas para 20+ moléculas del corpus panameño
- [ ] Precisión@1, @3, @5 calculadas para GNNExplainer y Grad-CAM
- [ ] Comparación de coherencia: GNNExplainer vs Grad-CAM documentada
- [ ] Galería de imágenes en `outputs/xai/figures/` (SVG por molécula)
- [ ] `notebooks/05_xai_analysis.ipynb` con análisis completo
- [ ] Al menos 3 casos de estudio detallados (molécula → predicción → explicación → validación química)
- [ ] Validación GHS: correlacionar predicciones del modelo con etiquetas H300-H361 de `pubchem_ghs_labels.csv`
- [ ] `notebooks/07_ghs_validation.ipynb` — tabla de coherencia predicción vs GHS por familia de plaguicida

---

## Fase V — Aplicación a Panamá

**Duración estimada:** 2 semanas  
**Objetivo:** Resultados aplicados al contexto panameño + comunicación para actores institucionales

### Análisis del corpus panameño

```python
# notebooks/06_panama_application.ipynb

TAREAS_TOX21 = [
    'NR-AR', 'NR-AR-LBD', 'NR-AhR', 'NR-Aromatase',
    'NR-ER', 'NR-ER-LBD', 'NR-PPAR-g',
    'SR-ARE', 'SR-AtAD5', 'SR-HSE', 'SR-MMP', 'SR-p53'
]

def generate_panama_report(model, explainer, panama_corpus):
    """
    Para cada plaguicida panameño:
    1. Predice probabilidad de toxicidad en las 12 vías
    2. Genera explicación XAI con GNNExplainer
    3. Identifica grupos funcionales de alta importancia
    4. Compara con datos experimentales de PPDB
    """
    report = []
    for compound_name, data in panama_corpus:
        # Predicción
        logits = model(data.x, data.edge_index,
                       torch.zeros(data.x.size(0), dtype=torch.long))
        probs  = torch.sigmoid(logits).squeeze().tolist()

        # XAI — diana con mayor probabilidad
        max_task = int(np.argmax(probs))
        node_imp, edge_imp = explain_molecule(explainer, data, max_task)

        # Grupos funcionales identificados
        top_atoms = node_imp.argsort(descending=True)[:5].tolist()

        report.append({
            'compuesto':       compound_name,
            'tarea_critica':   TAREAS_TOX21[max_task],
            'prob_max':        max(probs),
            'perfil_completo': dict(zip(TAREAS_TOX21, probs)),
            'atomos_clave':    top_atoms,
            'alerta':          'ALTO RIESGO' if max(probs) > 0.7 else
                               'RIESGO MODERADO' if max(probs) > 0.4 else
                               'BAJO RIESGO',
        })

    return pd.DataFrame(report)
```

### Casos de estudio prioritarios

| Compuesto | Por qué es prioritario | Vía de toxicidad esperada | Grupo funcional clave |
|---|---|---|---|
| **Clorpirifos** | Plaguicida más usado en banano de Panamá | SR-ARE, NR-AhR | Grupo fosforotioato P=S |
| **Atrazina** | Herbicida en caña de azúcar — disruptor endocrino conocido | NR-AR, NR-ER | Anillo triazina con -Cl |
| **Tebuconazol** | Fungicida en banano — inhibe CYP450 | NR-Aromatase, NR-PPAR-g | Anillo triazol + -Cl |
| **Cipermetrina** | Piretroide de uso general — tóxico para SNC | SR-HSE, SR-MMP | Éster + CN (ciano) |
| **Paraquat** | Herbicida — estrés oxidativo severo | SR-ARE, SR-p53 | Catión bipiridilo |
| **Glifosato** | Herbicida más vendido — controversia ARE | SR-ARE | Grupo fosfonato + amina |

### Generación de reporte institucional

```markdown
## Plantilla de reporte para MIDA/MINSA

# Perfil de Toxicidad Computacional — [Nombre del compuesto]

**Ingrediente activo:** [nombre]
**Número de registro MIDA:** [registro]
**SMILES canónico:** [smiles]
**Fecha de análisis:** [fecha]

## Predicciones de toxicidad

| Vía biológica | Probabilidad | Nivel de riesgo |
|---|---|---|
| Receptor de andrógenos (NR-AR) | X.XX | ALTO/MEDIO/BAJO |
| Receptor de estrógenos (NR-ER) | X.XX | ALTO/MEDIO/BAJO |
| Estrés oxidativo (SR-ARE)      | X.XX | ALTO/MEDIO/BAJO |
| Daño al ADN (SR-p53)           | X.XX | ALTO/MEDIO/BAJO |
| [... 8 vías adicionales]       | X.XX | ... |

## Grupos funcionales responsables

[Imagen de la molécula con átomos coloreados por importancia XAI]

El modelo identifica como grupos de mayor contribución:
- Átomo X ([símbolo]) — importancia: 0.XX
- Átomo Y ([símbolo]) — importancia: 0.XX
- Átomo Z ([símbolo]) — importancia: 0.XX

**Coherencia química:** [Descripción del mecanismo conocido]

## Comparación con datos experimentales

| Fuente | Dato experimental | Predicción modelo | Coincidencia |
|---|---|---|---|
| PPDB | [dato] | [predicción] | ✓/✗ |

## Recomendaciones

[Basadas en el perfil de toxicidad predicho]
```

### Entregables Fase V

- [ ] `outputs/reports/panama_pesticides_profile.csv` — perfil completo de 15+ plaguicidas
- [ ] `outputs/reports/report_mida_minsa.pdf` — reporte interpretado para actores no técnicos
- [ ] 6 casos de estudio completos con visualizaciones XAI
- [ ] Comparación predicciones vs datos PPDB documentada
- [ ] `notebooks/06_panama_application.ipynb` completo
- [ ] Presentación JIC preparada con: narrativa, metodología, 3 casos de estudio, conclusiones

---

## Stack tecnológico

| Categoría | Herramienta | Versión | Rol |
|---|---|---|---|
| Química computacional | **RDKit** | ≥ 2023.09 | Canonicalización, grafos, fingerprints, visualización |
| Deep learning | **PyTorch** | ≥ 2.0 | Framework principal, backprop, GPU |
| GNN | **PyTorch Geometric** | ≥ 2.4 | GINConv, pooling, GNNExplainer, batching |
| XAI | **Captum** | Última | Grad-CAM adaptado a grafos |
| Datasets | **DeepChem** | ≥ 2.7 | Loader Tox21, scaffold split, métricas |
| Logging | **Weights & Biases** | Última | Tracking de experimentos, curvas, reproducibilidad |
| Visualización | **matplotlib + seaborn** | — | Curvas ROC, mapas de calor AUC |
| Datos externos | **PPDB** | — | Datos experimentales de plaguicidas para validación |
| Cómputo | **Google Colab Pro** | GPU A100 | 5-fold CV en ~4-6h |
| Control de versiones | **Git + GitHub** | — | Reproducibilidad, documentación |

### Instalación rápida

```bash
conda create -n toxgnn python=3.10
conda activate toxgnn
conda install -c conda-forge rdkit
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install torch_geometric torch_scatter torch_sparse
pip install deepchem wandb captum pandas scikit-learn matplotlib seaborn
```

---

## Métricas y criterios de éxito

### Modelo predictivo

| Métrica | Cálculo | Objetivo mínimo | Objetivo ideal |
|---|---|---|---|
| AUC-ROC promedio | Media de 12 AUC por tarea | > 0.82 | > 0.84 |
| AUC-ROC por tarea | Por cada una de las 12 dianas | > 0.75 en todas | > 0.80 en todas |
| Desviación estándar CV | Std entre 5 folds | < 0.02 | < 0.015 |
| Diferencia val/test | AUC_val − AUC_test | < 0.02 | < 0.01 |
| Supera RF baseline | AUC_GNN > AUC_RF | Obligatorio | +0.05 AUC |
| Supera SMILES2vec | AUC_GNN > AUC_S2V | Objetivo principal | +0.02 AUC |

### Interpretabilidad XAI

| Métrica | Definición | Objetivo |
|---|---|---|
| Precision@1 | % moléculas donde el átomo más importante pertenece al grupo funcional correcto | > 65% |
| Precision@3 | % moléculas donde al menos 1 de 3 átomos más importantes es correcto | > 80% |
| Fidelidad del subgrafo | AUC usando solo los 5 átomos más importantes vs AUC completo | Diferencia < 0.05 |
| Coherencia GNNExp vs GradCAM | Correlación de Spearman entre rankings de importancia | > 0.70 |

### Referencia de rendimiento en Tox21

```
Random Forest + Morgan ECFP4   →  AUC ~0.77  (Wu et al., MoleculeNet 2018)
MLP + Morgan ECFP4             →  AUC ~0.79  (Wu et al., MoleculeNet 2018)
SMILES2vec (CNN-GRU)           →  AUC ~0.81  (Goh et al., KDD 2018)
GCN                            →  AUC ~0.83  (Yang et al., 2019)
GIN (este proyecto — objetivo) →  AUC > 0.83
Attentive FP (ref. alta)       →  AUC ~0.85  (Xiong et al., JCIM 2020)
```

---

## Cronograma general

```
SEMANA  1   2   3   4   5   6   7   8   9  10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE I  ████████
  1.1 Entorno        ██
  1.2 Descarga datos   ██
  1.3 Grafo molecular    ██
  1.4 Scaffold split       ██
  1.5 Máscara NaN            █
  1.6 Corpus Panamá          ██

FASE II         ████████
  2.1 Baseline RF     ████
  2.2 Baseline MLP        ██
  2.3 SMILES2vec          ████

FASE III              ████████
  3.1 GIN impl.           ████
  3.2 5-fold CV               ████

FASE IV                       ████████
  4.1 GNNExplainer                ████
  4.2 Grad-CAM                        ██
  4.3 Validación química              ████

FASE V                                  ████████
  5.1 Corpus Panamá                         ████
  5.2 Reportes MIDA/MINSA                       ████
  5.3 Presentación JIC                          ████

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
●  Hito: Pipeline validado        → fin semana 2
●  Hito: Baselines superan ~0.77  → fin semana 3
●  Hito: GNN AUC > 0.82           → fin semana 6
●  Hito: XAI coherencia > 80%     → fin semana 8
●  Hito: Reportes MIDA listos     → fin semana 10
```

---

## Decisiones de diseño importantes

### Por qué grafos y no SMILES o descriptores

```
Descriptores moleculares  →  requieren ingeniería de características manual
                              >5000 descriptores posibles
                              no mapean directamente a átomos para XAI

SMILES como texto         →  pierde información topológica 3D
                              el mismo átomo puede estar en posiciones distintas
                              XAI sobre caracteres ≠ XAI sobre átomos

Grafo molecular (GNN)     →  representación nativa de la molécula
                              invariante a permutaciones de átomos
                              XAI directamente sobre átomos del grafo
                              sin ingeniería de características manual
```

### Por qué GIN y no GCN o GAT

```
GCN  →  usa media ponderada — no preserva multiplicidad de vecinos
         menos expresivo que GIN en la jerarquía 1-WL

GAT  →  mecanismo de atención útil pero con más parámetros
         los pesos de atención son interpretables pero no tan precisos
         como GNNExplainer

GIN  →  suma no ponderada — preserva multiplicidad
         máxima expresividad dentro de la clase 1-WL (Xu et al., 2019)
         conexiones residuales controlan over-smoothing
         mejor AUC en benchmarks moleculares
```

### Por qué scaffold split y no split aleatorio

```
Split aleatorio  →  moléculas similares en train y test
                     AUC inflado artificialmente hasta +15%
                     no evalúa generalización real

Scaffold split   →  moléculas con el mismo esqueleto en el mismo fold
                     evalúa generalización a nuevas familias moleculares
                     escenario real: predecir sobre compuestos nuevos
                     estándar en publicaciones de MoleculeNet
```

---

## Comandos frecuentes

```bash
# ── PubChem — descargar fuentes de datos ──────────────────────────────────

# Pipeline completo PubChem: Classification HID72 + Compound + BioAssay + GHS
python -c "from src.data.pubchem_api import build_full_panama_corpus; build_full_panama_corpus()"

# Solo el corpus panameño (SMILES desde PubChem Compound)
python -c "from src.data.pubchem_api import build_panama_cid_list, enrich_corpus_with_smiles; \
           build_panama_cid_list(); enrich_corpus_with_smiles('data/raw/pubchem_panama_cids.csv')"

# Solo las etiquetas GHS (para validación externa)
python -c "from src.data.pubchem_api import fetch_ghs_labels; \
           import pandas as pd; \
           cids = pd.read_csv('data/raw/pubchem_panama_cids.csv')['CID'].tolist(); \
           fetch_ghs_labels(cids)"

# Consulta rápida: SMILES de un plaguicida por nombre
python -c "
import requests
name = 'Chlorpyrifos'
url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/CanonicalSMILES/JSON'
print(requests.get(url).json()['PropertyTable']['Properties'][0])
"

# ── Pipeline de datos principal ────────────────────────────────────────────

# Construir grafos moleculares desde Tox21
python src/data/featurizer.py --input data/raw/tox21.csv \
                               --output data/processed/

# Construir grafos del corpus panameño desde PubChem
python src/data/featurizer.py --input data/raw/pubchem_panama_cids.csv \
                               --output data/processed/ \
                               --corpus-mode

# ── Entrenamiento ──────────────────────────────────────────────────────────

# Entrenar baselines
python scripts/fase2/train_baselines.py --config config/config.yaml

# Entrenar GNN-GIN (un fold)
python scripts/fase3/train_gin.py --config config/config.yaml --fold 0

# 5-fold Cross-Validation completo
python scripts/run_cv.py --config config/config.yaml

# ── XAI y reportes ────────────────────────────────────────────────────────

# Generar explicaciones XAI para corpus panameño
python scripts/fase5/explain_panama.py --model outputs/models/best_gin_model.pt \
                                  --corpus data/processed/panama_corpus.pt

# Validar predicciones contra etiquetas GHS de PubChem
python scripts/fase5/validate_ghs.py --predictions outputs/results/panama_predictions.csv \
                                --ghs data/raw/pubchem_ghs_labels.csv \
                                --output outputs/reports/ghs_validation.csv

# Generar reporte MIDA/MINSA
python scripts/fase5/generate_report.py --results outputs/xai/ \
                                   --output outputs/reports/
```

---

## Referencias

1. Xu, K., Hu, W., Leskovec, J., & Jegelka, S. (2019). **How Powerful are Graph Neural Networks?** ICLR 2019.
2. Ying, R., et al. (2019). **GNNExplainer: Generating Explanations for Graph Neural Networks.** NeurIPS 2019.
3. Selvaraju, R.R., et al. (2017). **Grad-CAM: Visual Explanations from Deep Networks.** ICCV 2017.
4. Wu, Z., et al. (2018). **MoleculeNet: A Benchmark for Molecular Machine Learning.** Chemical Science.
5. Goh, G.B., et al. (2018). **SMILES2vec.** KDD 2018.
6. Xiong, Z., et al. (2020). **Attentive FP.** Journal of Chemical Information and Modeling.
7. Fey, M., & Lenssen, J.E. (2019). **Fast Graph Representation Learning with PyTorch Geometric.** ICLR Workshop.
8. Kim, S., et al. (2023). **PubChem 2023 update.** Nucleic Acids Research, 51(D1), D1373-D1380. https://pubchem.ncbi.nlm.nih.gov
9. MIDA — Ministerio de Desarrollo Agropecuario de Panamá. Registro Nacional de Plaguicidas. https://www.mida.gob.pa
10. PPDB — Pesticide Properties DataBase. University of Hertfordshire. https://sitem.herts.ac.uk/aeru/ppdb/
11. PubChem BioAssay — Tox21 AIDs. National Institutes of Health. https://pubchem.ncbi.nlm.nih.gov/bioassay
12. PubChem Classification — Pesticides (HID 72). https://pubchem.ncbi.nlm.nih.gov/classification/#hid=72
13. PubChem PUG REST API. https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest

---

*CLAUDE.md — Proyecto GNN + XAI para Toxicidad de Agroquímicos en Panamá · 2025*
