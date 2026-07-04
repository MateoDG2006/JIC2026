"""
Diagrama del proceso ETL del proyecto (Tox21 + Corpus Panama + ChEMBL).
Genera outputs/poster/fig5_etl.png
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PURPLE = "#2E2A6E"
CORAL  = "#E8654F"
GREEN  = "#3FA776"
GOLD   = "#E9A23B"
INK    = "#1E1E28"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
    "figure.dpi": 200,
})

fig, ax = plt.subplots(figsize=(13.5, 7.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# ---------- Encabezados de fase ETL ----------
phases = [("EXTRACCIÓN", 20), ("TRANSFORMACIÓN / LIMPIEZA", 50), ("CARGA — DATOS LISTOS", 80)]
for name, xc in phases:
    ax.text(xc, 95, name, ha="center", va="center", fontsize=14.5,
            fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.5", fc=PURPLE, ec="none"))

# separadores verticales de fase
for xsep in (35, 65):
    ax.plot([xsep, xsep], [4, 89], color="#D2D2DC", ls="--", lw=1, zorder=0)


def box(xc, yc, w, h, title, lines, color, fc_light):
    x0, y0 = xc - w/2, yc - h/2
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                 boxstyle="round,pad=0.6,rounding_size=2.2",
                 fc=fc_light, ec=color, lw=2.0, zorder=3))
    ax.text(xc, y0 + h - 4.4, title, ha="center", va="center",
            fontsize=11.5, fontweight="bold", color=color, zorder=4)
    ax.text(xc, y0 + (h-6)/2 - 1.2, "\n".join(lines), ha="center", va="center",
            fontsize=9.6, color=INK, zorder=4, linespacing=1.5)


def arrow(x0, x1, y, label=None):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y),
                 arrowstyle="-|>", mutation_scale=20,
                 color="#666", lw=2.2, zorder=2))
    if label:
        ax.text((x0+x1)/2, y+2.6, label, ha="center", va="bottom",
                fontsize=8.3, color="#B23A2E", style="italic")


# ============ CARRIL 1 — Tox21 (entrenamiento) ============
y1 = 74
box(20, y1, 26, 20, "Tox21  (MoleculeNet + PubChem BioAssay)",
    ["12 ensayos Tox21 (AIDs NIH)", "7 831 moléculas", "93 972 mediciones posibles"],
    PURPLE, "#EAE9F5")
box(50, y1, 26, 20, "Limpieza + featurización",
    ["− 8 SMILES inválidos (RDKit)", "16 026 NaN → máscara", "SMILES → grafo molecular"],
    PURPLE, "#EAE9F5")
box(80, y1, 26, 20, "Grafos Tox21  (scaffold split)",
    ["7 823 grafos válidos", "train 6 258 / val 782 / test 783", "77 946 mediciones útiles"],
    GREEN, "#E6F4EC")
arrow(33.5, 36.5, y1)
arrow(63.5, 66.5, y1)

# ============ CARRIL 2 — Corpus Panamá ============
y2 = 47
box(20, y2, 26, 18, "PubChem  (MIDA + árbol HID 72)",
    ["Ingredientes activos MIDA", "+ familias de plaguicidas", "CIDs recolectados"],
    PURPLE, "#EAE9F5")
box(50, y2, 26, 18, "Enriquecido + validación",
    ["SMILES canónicos (PubChem)", "Validación con RDKit", "Deduplicación por CID"],
    PURPLE, "#EAE9F5")
box(80, y2, 26, 18, "Corpus panameño",
    ["235 agroquímicos válidos", "+ etiquetas GHS (H-codes)", "→ aplicación del modelo"],
    GREEN, "#E6F4EC")
arrow(33.5, 36.5, y2)
arrow(63.5, 66.5, y2)

# ============ CARRIL 3 — ChEMBL ============
y3 = 20
box(20, y3, 26, 18, "ChEMBL  (bioactividad experimental)",
    ["Ensayos de plaguicidas Panamá", "10 745 registros crudos"],
    PURPLE, "#EAE9F5")
box(50, y3, 26, 18, "Filtros de calidad",
    ["Deduplicación + relación estándar", "Imputación de pChEMBL", "Descriptores moleculares"],
    PURPLE, "#EAE9F5")
box(80, y3, 26, 18, "ChEMBL limpio",
    ["2 807 registros de bioactividad", "→ validación externa"],
    GOLD, "#FBF0DD")
arrow(33.5, 36.5, y3)
arrow(63.5, 66.5, y3)

ax.set_title("Proceso ETL de los datos — GNN-GIN + XAI para toxicidad de agroquímicos",
             fontsize=15.5, fontweight="bold", color=PURPLE, pad=14)

plt.tight_layout()
plt.savefig("outputs/poster/fig5_etl.png", bbox_inches="tight")
plt.close()
print("Generado outputs/poster/fig5_etl.png")
