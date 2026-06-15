"""
Modelos baseline para comparar contra la GNN-GIN.

Estos son 3 modelos INDEPENDIENTES que sirven como referencia:
  1. Random Forest + fingerprints Morgan ECFP4 (AUC esperado ~0.77)
  2. MLP + fingerprints Morgan ECFP4 (AUC esperado ~0.79)
  3. SMILES2vec CNN-GRU (AUC esperado ~0.81)

Si la GNN no supera a estos baselines, algo está mal.
Si el RF no llega a ~0.72-0.76 con scaffold split, los datos tienen un bug.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from rdkit import Chem
from sklearn.ensemble import RandomForestClassifier

try:
    from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator
except ImportError:
    GetMorganGenerator = None  # type: ignore[misc, assignment]


# ── Fingerprints Morgan (ECFP4) ──────────────────────────────────────────

def morgan_fingerprints(
    smiles_list: list[str],
    radius: int = 2,
    n_bits: int = 2048,
) -> np.ndarray:
    """Genera fingerprints Morgan ECFP4 para una lista de SMILES.

    Un fingerprint es un vector binario de 2048 bits que codifica
    los subestructuras circulares de radio 2 alrededor de cada átomo.
    Es la representación clásica para modelos de ML en quimioinformática.

    SMILES inválidos generan un vector de ceros (en vez de fallar).
    """
    fps: list[list[int]] = []
    if GetMorganGenerator is not None:
        mfpgen = GetMorganGenerator(radius=radius, fpSize=n_bits)
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                fps.append([0] * n_bits)
                continue
            fp = mfpgen.GetFingerprint(mol)
            fps.append(list(fp))
    else:
        from rdkit.Chem import AllChem
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                fps.append([0] * n_bits)
                continue
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
            fps.append(list(fp))
    return np.asarray(fps, dtype=np.float32)


# ── Baseline 1: Random Forest ────────────────────────────────────────────

class RandomForestBaseline:
    """Un Random Forest separado por cada tarea Tox21.

    Entrena 12 clasificadores independientes, cada uno solo con las
    muestras que tienen medición para esa tarea (mask=True).
    Usa class_weight='balanced_subsample' para compensar el desbalance.
    """

    def __init__(
        self,
        n_estimators: int = 800,
        n_jobs: int = -1,
        *,
        verbose: bool = False,
        sklearn_fit_verbose: int = 0,
    ) -> None:
        self.n_estimators = n_estimators
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.sklearn_fit_verbose = sklearn_fit_verbose
        self._estimators: list[RandomForestClassifier | None] = []

    def fit(self, smiles_list: list[str], y: np.ndarray, mask: np.ndarray) -> None:
        """Entrena un RF por tarea usando solo muestras con medición."""
        X = morgan_fingerprints(smiles_list)
        n_tasks = y.shape[1]
        self._estimators = []
        for t in range(n_tasks):
            m = mask[:, t].astype(bool)
            y_t = np.clip(np.nan_to_num(y[m, t], nan=0.0), 0.0, 1.0)
            y_t = np.rint(y_t).astype(np.int64)
            if m.sum() < 2 or len(np.unique(y_t)) < 2:
                self._estimators.append(None)
                if self.verbose:
                    print(f"    [{t + 1}/{n_tasks}] omitida "
                          f"(pocas muestras o una sola clase)", flush=True)
                continue
            if self.verbose:
                n_pos = int((y_t == 1).sum())
                print(f"    [{t + 1}/{n_tasks}] RandomForest "
                      f"(n={int(m.sum())}, positivos={n_pos}, "
                      f"árboles={self.n_estimators})...", flush=True)
            clf = RandomForestClassifier(
                n_estimators=self.n_estimators,
                n_jobs=self.n_jobs,
                max_features="sqrt",
                class_weight="balanced_subsample",
                criterion="log_loss",
                random_state=42,
                verbose=self.sklearn_fit_verbose,
            )
            clf.fit(X[m], y_t)
            self._estimators.append(clf)

    def predict_proba(self, smiles_list: list[str]) -> np.ndarray:
        """Predice probabilidades para todas las tareas."""
        X = morgan_fingerprints(smiles_list)
        n = X.shape[0]
        n_tasks = len(self._estimators)
        probs = np.zeros((n, n_tasks), dtype=np.float64)
        for t, clf in enumerate(self._estimators):
            if self.verbose:
                print(f"    RF predict_proba tarea {t + 1}/{n_tasks}...", flush=True)
            if clf is None:
                probs[:, t] = 0.5
                continue
            p = clf.predict_proba(X)
            if p.shape[1] >= 2:
                classes = np.asarray(clf.classes_)
                hit = np.flatnonzero(np.isclose(classes, 1.0) | (classes == 1))
                pos_idx = int(hit[0]) if hit.size else int(np.argmax(classes))
                probs[:, t] = p[:, pos_idx]
            else:
                probs[:, t] = 1.0 if clf.classes_[0] == 1 else 0.0
        return probs


# ── Baseline 2: MLP ──────────────────────────────────────────────────────

class MLPBaseline(nn.Module):
    """Red neuronal feedforward con 2 capas ocultas.

    Recibe fingerprints Morgan (2048 bits) y predice 12 tareas.
    Arquitectura: 2048 → 512 → 256 → 12
    """

    def __init__(
        self,
        input_dim: int = 2048,
        hidden_dim: int = 512,
        n_tasks: int = 12,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        h2 = hidden_dim // 2
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, h2),
            nn.BatchNorm1d(h2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(h2, n_tasks),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Retorna logits (sin sigmoid). Aplicar sigmoid para probabilidades."""
        return self.net(x)


# ── Vocabulario SMILES para SMILES2vec ────────────────────────────────────

# Mapa de caracteres SMILES → índices enteros para el embedding.
# El padding usa índice 0 (espacio).
_SMILES_ORDERED_UNIQUE: list[str] = []
for ch in (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "()[]=#@+-\\/.*%$^~:|?<>"
):
    if ch not in _SMILES_ORDERED_UNIQUE:
        _SMILES_ORDERED_UNIQUE.append(ch)
CHAR_TO_IDX: dict[str, int] = {c: i + 1 for i, c in enumerate(_SMILES_ORDERED_UNIQUE)}
CHAR_TO_IDX[" "] = 0  # padding
VOCAB_SIZE = max(CHAR_TO_IDX.values()) + 1


def smiles_to_indices(smiles: str, max_len: int = 250) -> list[int]:
    """Convierte un SMILES a una secuencia de índices enteros.
    Trunca a max_len caracteres y rellena con espacios (índice 0)."""
    s = smiles[:max_len].ljust(max_len)
    return [CHAR_TO_IDX.get(c, 0) for c in s]


# ── Baseline 3: SMILES2vec (CNN-GRU) ─────────────────────────────────────

class SMILES2vec(nn.Module):
    """Modelo CNN-GRU que lee SMILES como texto (Goh et al. KDD 2018).

    Pipeline interno:
      1. Embedding: cada caracter → vector de 50 dims
      2. Conv1D: extrae patrones locales de 3 caracteres
      3. GRU bidireccional (2 capas): captura dependencias secuenciales
      4. Clasificador: último estado oculto → 12 tareas

    Usa h_n (estado oculto final) del GRU en lugar del último timestep
    de la secuencia de salida, que es más estable para clasificación.
    """

    def __init__(
        self,
        vocab_size: int = VOCAB_SIZE,
        embed_dim: int = 50,
        conv_filters: int = 192,
        gru1_units: int = 224,
        gru2_units: int = 384,
        n_tasks: int = 12,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.conv = nn.Conv1d(embed_dim, conv_filters, kernel_size=3, padding=1)
        self.gru1 = nn.GRU(
            conv_filters, gru1_units, batch_first=True, bidirectional=True
        )
        self.gru2 = nn.GRU(
            gru1_units * 2, gru2_units, batch_first=True, bidirectional=True
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(gru2_units * 2, n_tasks),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len) — índices enteros de caracteres SMILES."""
        # Embedding: (batch, seq_len) → (batch, seq_len, embed_dim)
        emb = self.embedding(x)
        # Conv1D espera (batch, channels, seq_len)
        emb = emb.permute(0, 2, 1)
        conv = torch.relu(self.conv(emb)).permute(0, 2, 1)
        # GRU bidireccional: procesa la secuencia en ambas direcciones
        out1, _ = self.gru1(conv)
        # h_n: (2, batch, gru2_units) — 2 direcciones
        _, h_n = self.gru2(out1)
        # Concatenar las 2 direcciones del estado oculto final
        h_final = torch.cat([h_n[0], h_n[1]], dim=-1)
        return self.classifier(h_final)
