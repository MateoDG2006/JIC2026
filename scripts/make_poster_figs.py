"""
Genera las figuras del poster JIC 2026 a partir de los resultados REALES del proyecto
GNN-GIN + XAI para toxicidad de agroquimicos. Sustituye el contenido erroneo de PFH/FPFH.
Salida: outputs/poster/*.png
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ----- Paleta coherente con el poster -----
PURPLE = "#2E2A6E"
CORAL  = "#E8654F"
GREEN  = "#3FA776"
GREY   = "#B9B9C6"
GOLD   = "#E9A23B"
plt.rcParams.update({
    "font.family": "DejaVu Sans",   # soporta acentos y ñ
    "font.size": 13,
    "axes.edgecolor": "#555",
    "axes.linewidth": 0.9,
    "figure.dpi": 200,
    "axes.unicode_minus": False,
})

TASKS = ['NR-AR','NR-AR-LBD','NR-AhR','NR-Aromatase','NR-ER','NR-ER-LBD',
         'NR-PPAR-gamma','SR-ARE','SR-AtAD5','SR-HSE','SR-MMP','SR-p53']

OUT = "outputs/poster"

# ================================================================
# FIG 1 - Comparacion de modelos (Media AUC-ROC)  [seccion METRICAS]
# ================================================================
base = pd.read_csv("outputs/results/baseline_results.csv")
cv   = pd.read_csv("outputs/results/gin_cv_summary.csv")

rf  = float(base.loc[base.Modelo=="Random Forest","Media AUC-ROC"].iloc[0])
mlp = float(base.loc[base.Modelo=="MLP","Media AUC-ROC"].iloc[0])
s2v = float(base.loc[base.Modelo=="SMILES2vec","Media AUC-ROC"].iloc[0])
gin_mean = cv["mean_auc"].mean()
gin_std  = cv["mean_auc"].std(ddof=1)

models = ["Random\nForest", "MLP", "SMILES2vec", "GNN-GIN\n(este trabajo)"]
vals   = [rf, mlp, s2v, gin_mean]
errs   = [0, 0, 0, gin_std]
colors = [GREY, GREY, GREY, PURPLE]

fig, ax = plt.subplots(figsize=(7.2, 4.6))
bars = ax.bar(models, vals, yerr=errs, capsize=6, color=colors, edgecolor="#333", width=0.62)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.012, f"{v:.3f}",
            ha="center", va="bottom", fontsize=13, fontweight="bold")
ax.axhline(0.5, color="#999", ls=":", lw=1)
ax.text(3.45, 0.51, "azar (0.50)", color="#777", fontsize=9, ha="right")
ax.set_ylim(0.45, 0.86)
ax.set_ylabel("Media AUC-ROC (12 tareas Tox21)")
ax.set_title("Comparación de modelos  ·  scaffold split, 5-fold CV",
             fontweight="bold", color=PURPLE, fontsize=14, pad=10)
ax.spines[["top","right"]].set_visible(False)
ax.legend(handles=[Patch(facecolor=GREY, label="Baselines"),
                   Patch(facecolor=PURPLE, label="GNN-GIN")],
          loc="upper left", frameon=False, fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT}/fig1_comparacion_modelos.png", bbox_inches="tight")
plt.close()

# ================================================================
# FIG 2 - AUC-ROC por tarea (GIN)  [seccion RESULTADOS]
# ================================================================
gin = pd.read_csv("outputs/results/gin_results.csv").iloc[0]
per_task = np.array([gin[t.replace("NR-PPAR-gamma","NR-PPAR-gamma")] for t in TASKS], dtype=float)

order = np.argsort(per_task)[::-1]
tsorted = [TASKS[i] for i in order]
vsorted = per_task[order]
bar_colors = [GREEN if v>=0.80 else (CORAL if v<0.70 else PURPLE) for v in vsorted]

fig, ax = plt.subplots(figsize=(8.4, 4.6))
bars = ax.bar(range(len(tsorted)), vsorted, color=bar_colors, edgecolor="#333", width=0.72)
for i, v in enumerate(vsorted):
    ax.text(i, v+0.008, f"{v:.2f}", ha="center", va="bottom", fontsize=10.5)
ax.axhline(0.75, color="#666", ls="--", lw=1.1)
ax.text(len(tsorted)-0.4, 0.755, "umbral 0.75", color="#666", fontsize=9.5, ha="right")
ax.set_xticks(range(len(tsorted)))
ax.set_xticklabels(tsorted, rotation=40, ha="right", fontsize=10.5)
ax.set_ylim(0.60, 0.88)
ax.set_ylabel("AUC-ROC (test)")
ax.set_title("Desempeño del GNN-GIN por diana biológica Tox21",
             fontweight="bold", color=PURPLE, fontsize=14, pad=10)
ax.spines[["top","right"]].set_visible(False)
ax.legend(handles=[Patch(facecolor=GREEN, label="Alta (≥ 0.80)"),
                   Patch(facecolor=PURPLE, label="Media"),
                   Patch(facecolor=CORAL, label="Baja (< 0.70)")],
          loc="upper right", frameon=False, fontsize=10, ncol=3)
plt.tight_layout()
plt.savefig(f"{OUT}/fig2_auc_por_tarea.png", bbox_inches="tight")
plt.close()

# ================================================================
# FIG 3 - Aplicacion al corpus panameno  [seccion COMPARACION/APLICACION]
#   (a) distribucion de alertas   (b) prob media por via
# ================================================================
pan = pd.read_csv("outputs/results/panama_predictions.csv")
alert_order = ["ALTO","MODERADO","BAJO"]
counts = [ (pan["alerta"]==a).sum() for a in alert_order ]
acolors = [CORAL, GOLD, GREEN]

mean_prob = pan[TASKS].mean().sort_values(ascending=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.4),
                               gridspec_kw={"width_ratios":[1, 1.35]})

# (a) alertas
b = ax1.bar(alert_order, counts, color=acolors, edgecolor="#333", width=0.6)
for bar, c in zip(b, counts):
    ax1.text(bar.get_x()+bar.get_width()/2, c+3, str(c), ha="center", fontweight="bold")
ax1.set_ylabel("N.º de agroquímicos")
ax1.set_title(f"Nivel de riesgo  (n={len(pan)})", fontweight="bold", color=PURPLE, fontsize=13)
ax1.spines[["top","right"]].set_visible(False)
ax1.set_ylim(0, max(counts)*1.18)

# (b) prob media por via
yc = [CORAL if v>=0.15 else (PURPLE if v>=0.08 else GREY) for v in mean_prob.values]
ax2.barh(range(len(mean_prob)), mean_prob.values, color=yc, edgecolor="#333")
ax2.set_yticks(range(len(mean_prob)))
ax2.set_yticklabels(mean_prob.index, fontsize=10)
for i, v in enumerate(mean_prob.values):
    ax2.text(v+0.004, i, f"{v:.2f}", va="center", fontsize=9.5)
ax2.set_xlabel("Probabilidad media predicha")
ax2.set_title("Vías de toxicidad predominantes", fontweight="bold", color=PURPLE, fontsize=13)
ax2.spines[["top","right"]].set_visible(False)
ax2.set_xlim(0, mean_prob.max()*1.22)
plt.tight_layout()
plt.savefig(f"{OUT}/fig3_aplicacion_panama.png", bbox_inches="tight")
plt.close()

# ================================================================
# FIG 4 - Estabilidad 5-fold CV  [reemplaza seccion de descriptores]
#   (a) AUC media por fold + banda media±std   (b) heatmap tarea x fold
# ================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.6),
                               gridspec_kw={"width_ratios":[1, 1.55]})

# (a) AUC por fold
folds = cv["fold"].astype(int).values
fauc  = cv["mean_auc"].values
b = ax1.bar([f"Fold {f}" for f in folds], fauc, color=PURPLE, edgecolor="#333", width=0.62)
for bar, v in zip(b, fauc):
    ax1.text(bar.get_x()+bar.get_width()/2, v+0.004, f"{v:.3f}",
             ha="center", va="bottom", fontsize=10.5, fontweight="bold")
ax1.axhline(gin_mean, color=CORAL, lw=1.8)
ax1.fill_between([-0.5, len(folds)-0.5], gin_mean-gin_std, gin_mean+gin_std,
                 color=CORAL, alpha=0.15, zorder=0)
ax1.text(len(folds)-0.55, gin_mean+gin_std+0.002,
         f"media = {gin_mean:.3f} ± {gin_std:.3f}", color=CORAL,
         fontsize=10.5, ha="right", fontweight="bold")
ax1.set_xlim(-0.5, len(folds)-0.5)
ax1.set_ylim(0.70, 0.84)
ax1.set_ylabel("AUC-ROC media (test)")
ax1.set_title("Estabilidad entre folds", fontweight="bold", color=PURPLE, fontsize=13)
ax1.spines[["top","right"]].set_visible(False)
ax1.tick_params(axis="x", labelrotation=0)

# (b) heatmap tarea x fold
mat = cv[TASKS].values.T  # (12 tareas x 5 folds)
im = ax2.imshow(mat, aspect="auto", cmap="RdYlGn", vmin=0.60, vmax=0.95)
ax2.set_xticks(range(len(folds)))
ax2.set_xticklabels([f"F{f}" for f in folds], fontsize=10)
ax2.set_yticks(range(len(TASKS)))
ax2.set_yticklabels(TASKS, fontsize=9)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax2.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center",
                 fontsize=8, color="#222")
ax2.set_title("AUC-ROC por tarea y fold", fontweight="bold", color=PURPLE, fontsize=13)
cbar = fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.02)
cbar.set_label("AUC-ROC", fontsize=10)
plt.tight_layout()
plt.savefig(f"{OUT}/fig4_folds_cv.png", bbox_inches="tight")
plt.close()

print("Figuras generadas:")
print(f"  gin_mean={gin_mean:.4f} +/- {gin_std:.4f}")
print(f"  RF={rf:.4f}  MLP={mlp:.4f}  S2V={s2v:.4f}")
print(f"  alertas: ALTO={counts[0]} MOD={counts[1]} BAJO={counts[2]}")
