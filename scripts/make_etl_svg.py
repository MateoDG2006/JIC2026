"""
Genera un diagrama ETL vectorial (SVG) con iconos dibujados a mano.
Salida: outputs/poster/fig5_etl.svg  y un wrapper HTML para rasterizar.
"""
from pathlib import Path

PURPLE = "#2E2A6E"
CORAL  = "#E8654F"
GREEN  = "#2E9E68"
GOLD   = "#E09A2B"
INK    = "#2A2A34"
LILAC  = "#EEEDF7"
MINT   = "#E4F3EA"
CREAM  = "#FBF0DA"

W, H = 1380, 580

# ---------------- Iconos (vectoriales) ----------------
def molecule(cx, cy, c):
    r = 6
    pts = [(cx-16, cy+6), (cx, cy-12), (cx+16, cy+8)]
    bonds = f'<line x1="{pts[0][0]}" y1="{pts[0][1]}" x2="{pts[1][0]}" y2="{pts[1][1]}" stroke="{c}" stroke-width="2.4"/>' \
            f'<line x1="{pts[1][0]}" y1="{pts[1][1]}" x2="{pts[2][0]}" y2="{pts[2][1]}" stroke="{c}" stroke-width="2.4"/>' \
            f'<line x1="{pts[0][0]}" y1="{pts[0][1]}" x2="{pts[2][0]}" y2="{pts[2][1]}" stroke="{c}" stroke-width="2.4"/>'
    circ = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="{c}" stroke-width="2.4"/>' for x,y in pts)
    return f'<g>{bonds}{circ}</g>'

def database(cx, cy, c):
    return f'''<g fill="none" stroke="{c}" stroke-width="2.4">
      <ellipse cx="{cx}" cy="{cy-13}" rx="17" ry="6" fill="white"/>
      <path d="M{cx-17},{cy-13} V{cy+13} a17,6 0 0 0 34,0 V{cy-13}"/>
      <path d="M{cx-17},{cy} a17,6 0 0 0 34,0"/>
    </g>'''

def flask(cx, cy, c):
    return f'''<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linejoin="round">
      <path d="M{cx-6},{cy-16} V{cy-4} L{cx-15},{cy+14} a4,4 0 0 0 3.6,6 h22.8 a4,4 0 0 0 3.6,-6 L{cx+6},{cy-4} V{cy-16}"/>
      <line x1="{cx-9}" y1="{cy-16}" x2="{cx+9}" y2="{cy-16}"/>
      <path d="M{cx-11},{cy+6} h22" stroke="{c}" stroke-width="6" opacity="0.28"/>
    </g>'''

def funnel(cx, cy, c):
    return f'''<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linejoin="round">
      <path d="M{cx-16},{cy-14} h32 L{cx+4},{cy+2} v14 l-8,4 v-18 Z"/>
    </g>'''

def check(cx, cy, c):
    return f'''<g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="{cx}" cy="{cy}" r="16"/>
      <path d="M{cx-7},{cy} l5,5 l9,-11"/>
    </g>'''

# ---------------- Caja ----------------
def box(x, y, w, h, title, lines, border, fill, icon_svg):
    tx = x + 58
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" '
           f'fill="{fill}" stroke="{border}" stroke-width="2.4"/>']
    # icono arriba-izquierda
    out.append(f'<g transform="translate({x+30},{y+34})">{icon_svg}</g>')
    out.append(f'<text x="{tx}" y="{y+40}" font-size="17" font-weight="700" '
               f'fill="{border}" font-family="DejaVu Sans, Arial, sans-serif">{title}</text>')
    ly = y + 68
    for ln in lines:
        out.append(f'<text x="{x+22}" y="{ly}" font-size="14.5" fill="{INK}" '
                   f'font-family="DejaVu Sans, Arial, sans-serif">{ln}</text>')
        ly += 24
    return "".join(out)

def arrow(x0, x1, y):
    return (f'<line x1="{x0}" y1="{y}" x2="{x1-12}" y2="{y}" stroke="#6C6C7A" stroke-width="3"/>'
            f'<path d="M{x1-12},{y-7} L{x1},{y} L{x1-12},{y+7} Z" fill="#6C6C7A"/>')

def pill(cx, y, text):
    w = 320
    return (f'<rect x="{cx-w/2}" y="{y}" width="{w}" height="46" rx="23" fill="{PURPLE}"/>'
            f'<text x="{cx}" y="{y+30}" text-anchor="middle" font-size="19" font-weight="700" '
            f'fill="white" font-family="DejaVu Sans, Arial, sans-serif">{text}</text>')

# ---------------- Composición ----------------
BW, BH = 300, 150
c1, c2, c3 = 235, 690, 1145
xcol = {c1: 85, c2: 540, c3: 995}
r1, r2 = 190, 380

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">']
svg.append(f'<rect width="{W}" height="{H}" fill="white"/>')

# título
svg.append(f'<text x="{W/2}" y="46" text-anchor="middle" font-size="26" font-weight="800" '
           f'fill="{PURPLE}">Proceso ETL de los datos</text>')
svg.append(f'<text x="{W/2}" y="74" text-anchor="middle" font-size="15" fill="#6C6C7A">'
           f'GNN-GIN + XAI para predicción de toxicidad de agroquímicos</text>')

# encabezados de fase
svg.append(pill(c1, 96, "1 · EXTRACCIÓN"))
svg.append(pill(c2, 96, "2 · LIMPIEZA"))
svg.append(pill(c3, 96, "3 · DATOS LISTOS"))

# separadores
for xs in (462, 918):
    svg.append(f'<line x1="{xs}" y1="150" x2="{xs}" y2="{H-30}" stroke="#D8D8E2" '
               f'stroke-width="1.5" stroke-dasharray="6 6"/>')

# ---- Carril 1: Tox21 ----
svg.append(box(xcol[c1], r1, BW, BH, "Tox21",
    ["MoleculeNet + PubChem", "12 ensayos (AIDs NIH)", "7 831 moléculas",
     "93 972 mediciones"], PURPLE, LILAC, molecule(0,0,PURPLE)))
svg.append(box(xcol[c2], r1, BW, BH, "Limpieza + featurización",
    ["− 8 SMILES inválidos (RDKit)", "16 026 NaN → máscara", "SMILES → grafo molecular",
     ""], PURPLE, LILAC, funnel(0,0,PURPLE)))
svg.append(box(xcol[c3], r1, BW, BH, "Grafos Tox21",
    ["7 823 grafos válidos", "train 6 258 · val 782 · test 783", "77 946 mediciones útiles",
     "scaffold split"], GREEN, MINT, check(0,0,GREEN)))
svg.append(arrow(xcol[c1]+BW, xcol[c2], r1+BH/2))
svg.append(arrow(xcol[c2]+BW, xcol[c3], r1+BH/2))

# ---- Carril 2: Corpus Panamá ----
svg.append(box(xcol[c1], r2, BW, BH, "PubChem",
    ["Ingredientes activos MIDA", "+ árbol HID 72 (plaguicidas)", "CIDs recolectados", ""],
    PURPLE, LILAC, database(0,0,PURPLE)))
svg.append(box(xcol[c2], r2, BW, BH, "Enriquecido + validación",
    ["SMILES canónicos (PubChem)", "Validación con RDKit", "Deduplicación por CID", ""],
    PURPLE, LILAC, funnel(0,0,PURPLE)))
svg.append(box(xcol[c3], r2, BW, BH, "Corpus panameño",
    ["235 agroquímicos válidos", "+ etiquetas GHS (H-codes)", "→ aplicación del modelo", ""],
    GREEN, MINT, check(0,0,GREEN)))
svg.append(arrow(xcol[c1]+BW, xcol[c2], r2+BH/2))
svg.append(arrow(xcol[c2]+BW, xcol[c3], r2+BH/2))

svg.append('</svg>')
svg_str = "\n".join(svg)

out = Path("outputs/poster")
(out / "fig5_etl.svg").write_text(svg_str, encoding="utf-8")

# wrapper HTML para rasterizar en navegador
html = f'''<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:white}}
#d{{width:{W}px}}</style></head>
<body><div id="d">{svg_str}</div></body></html>'''
(out / "etl_preview.html").write_text(html, encoding="utf-8")

print("Generado outputs/poster/fig5_etl.svg y etl_preview.html")
