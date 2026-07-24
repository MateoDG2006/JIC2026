from pathlib import Path
from urllib.parse import quote

body = Path(r"C:\Users\mateo\Desktop\PROYECTOS\JIC2026\viz\_landing_body_fragment.html").read_text(
    encoding="utf-8"
)

# Wire case study links to /analyze (not go-visor lights-out)
atr_smiles = quote("CCNc1nc(Cl)nc(NC(C)C)n1")
gly_smiles = quote("C(C(=O)O)NCP(=O)(O)O")

body = body.replace(
    '<a class="go go-visor" href="#"><span data-i18n="cases.go">Analizar en el visor</span> →</a>\n'
    "      </div>\n"
    '      <div class="case reveal d1">',
    f'<a class="go" href="/analyze?smiles={atr_smiles}&name=Atrazina&family=Triazinas">'
    '<span data-i18n="cases.go">Analizar en el visor</span> →</a>\n'
    "      </div>\n"
    '      <div class="case reveal d1">',
)
body = body.replace(
    '<a class="go go-visor" href="#"><span data-i18n="cases.go">Analizar en el visor</span> →</a>\n'
    "      </div>\n"
    "    </div>\n"
    "  </div>\n"
    "</section>\n"
    "\n"
    '<section id="xai">',
    f'<a class="go" href="/analyze?smiles={gly_smiles}&name=Glifosato&family=Herbicidas">'
    '<span data-i18n="cases.go">Analizar en el visor</span> →</a>\n'
    "      </div>\n"
    "    </div>\n"
    "  </div>\n"
    "</section>\n"
    "\n"
    '<section id="xai">',
)

# Brand home link
body = body.replace('<a class="brand" href="#top">', '<a class="brand" href="/">')

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GNN-Tox · Predicción de toxicidad de agroquímicos</title>
  <meta name="description" content="Predicción de toxicidad de agroquímicos con redes neuronales de grafos e inteligencia artificial explicable. JIC 2026 — Universidad Tecnológica de Panamá.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/landing.css">
</head>
<body>
{body}
<script src="/static/js/landing.js"></script>
</body>
</html>
"""

out = Path(r"C:\Users\mateo\Desktop\PROYECTOS\JIC2026\viz\templates\landing.html")
out.write_text(html, encoding="utf-8")
print("wrote", out, "bytes", out.stat().st_size)

# cleanup
for p in [
    Path(r"C:\Users\mateo\Desktop\PROYECTOS\JIC2026\viz\_extract_landing.py"),
    Path(r"C:\Users\mateo\Desktop\PROYECTOS\JIC2026\viz\_landing_body_fragment.html"),
]:
    p.unlink(missing_ok=True)
print("cleaned temp files")
