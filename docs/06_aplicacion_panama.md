# Aplicación al Contexto Panameño

**Módulo:** `notebooks/06_panama_application.ipynb`, `notebooks/07_ghs_validation.ipynb`  
**Fase:** V — Aplicación a Panamá (Semanas 9–10)

---

## Descripción

Aplica el modelo GNN-GIN entrenado y las explicaciones XAI al corpus de plaguicidas registrados en el MIDA de Panamá. Genera perfiles de toxicidad computacional y reportes interpretados para actores institucionales (MIDA, MINSA), con validación externa contra etiquetas GHS.

---

## Corpus panameño

El corpus se construyó en la Fase I desde PubChem con trazabilidad verificable. Cubre los principales plaguicidas de la agricultura de exportación panameña:

| Familia | Ejemplos | Cultivos principales |
|---|---|---|
| Organofosforados | Clorpirifos, Malatión, Dimetoato | Banano, arroz, caña |
| Carbamatos | Carbaryl, Metomilo, Aldicarb | Hortalizas, frutas |
| Triazinas | Atrazina, Simazina | Caña de azúcar, maíz |
| Fungicidas azólicos | Tebuconazol, Propiconazol | Banano, arroz |
| Piretroides | Cipermetrina, Deltametrina | Banano, hortalizas |
| Herbicidas | Glifosato, Paraquat, 2,4-D | Caña, banano, arroz |

---

## Perfil de toxicidad por plaguicida

Para cada compuesto del corpus se genera:

1. **Predicción de probabilidad** en las 12 vías Tox21
2. **Nivel de alerta** según la probabilidad máxima

```
P(toxicidad) > 0.7  →  ALTO RIESGO
P(toxicidad) > 0.4  →  RIESGO MODERADO
P(toxicidad) ≤ 0.4  →  BAJO RIESGO
```

3. **Tarea crítica**: diana biológica con mayor probabilidad predicha
4. **Átomos clave**: top-5 átomos por importancia XAI (GNNExplainer)
5. **Visualización molecular**: imagen SVG con colores de importancia

---

## Casos de estudio prioritarios

| Compuesto | Por qué es prioritario | Vía esperada | Grupo funcional clave |
|---|---|---|---|
| **Clorpirifos** | Más usado en banano de Panamá | SR-ARE, NR-AhR | Fosforotioato `P=S` |
| **Atrazina** | Disruptor endocrino conocido, caña de azúcar | NR-AR, NR-ER | Triazina con `-Cl` |
| **Tebuconazol** | Inhibe CYP450, banano | NR-Aromatase, NR-PPAR-γ | Triazol + `-Cl` |
| **Cipermetrina** | Tóxico para SNC, uso general | SR-HSE, SR-MMP | Éster + ciano `CN` |
| **Paraquat** | Estrés oxidativo severo, herbicida amplio | SR-ARE, SR-p53 | Catión bipiridilo |
| **Glifosato** | Herbicida más vendido — controversia ARE | SR-ARE | Fosfonato + amina |

---

## Validación con datos experimentales PPDB

La Pesticide Properties DataBase (PPDB) provee datos experimentales de toxicidad que sirven como referencia independiente:

| Fuente PPDB | Dato experimental | Correlación con Tox21 |
|---|---|---|
| DL50 oral (rata) | mg/kg | NR-AR, NR-ER (disruptores endocrinos) |
| DL50 dérmica | mg/kg | SR-MMP, SR-ARE |
| LC50 trucha (96h) | mg/L | Toxicidad acuática |
| Clasificación WHO | Clase I–IV | Alerta general |

---

## Validación externa: etiquetas GHS (PubChem)

Las etiquetas H-statements descargadas en la Fase I permiten una validación cruzada independiente del modelo:

| Código GHS | Significado | Correlación esperada con Tox21 |
|---|---|---|
| H300/H301/H302 | Toxicidad oral fatal/tóxica/nociva | SR-ARE, SR-MMP |
| H360/H361 | Toxicidad reproductiva | NR-AR, NR-ER |
| H340/H341 | Mutagenicidad | SR-p53, SR-AtAD5 |
| H350/H351 | Carcinogenicidad | SR-p53 |
| H400/H410/H411 | Toxicidad acuática aguda/crónica | — |

### Método de validación

```
Para cada plaguicida del corpus:
  predicción GNN (P > 0.5 → tóxico) vs etiqueta GHS (H300-H361 → tóxico)
  
Calcular: Sensibilidad, Especificidad, AUROC
  por familia de plaguicida y por diana biológica
```

---

## Reporte para MIDA/MINSA

Cada reporte incluye:

```markdown
# Perfil de Toxicidad Computacional — [Nombre del compuesto]

Ingrediente activo: [nombre]
Número de registro MIDA: [registro]
SMILES canónico: [smiles]

## Predicciones de toxicidad
| Vía biológica          | Probabilidad | Nivel de riesgo |
|------------------------|--------------|-----------------|
| Receptor de andrógenos | 0.73         | ALTO RIESGO     |
| Estrés oxidativo       | 0.61         | ALTO RIESGO     |
| Daño al ADN (p53)      | 0.38         | RIESGO MODERADO |
...

## Grupos funcionales responsables
[Imagen SVG de la molécula con átomos coloreados]

Los átomos de mayor contribución identificados son:
- Átomo P (fósforo) — importancia: 0.91 → grupo fosforotioato P=S
- Átomo Cl (cloro) — importancia: 0.74 → sustituyente halogenado

## Comparación con datos experimentales
| Fuente | Dato | Predicción | Coincidencia |
| PPDB   | DL50 oral: 135 mg/kg (Clase II WHO) | NR-AR: ALTO RIESGO | ✓ |
```

---

## Archivos de salida

```
outputs/reports/
├── panama_pesticides_profile.csv      # perfil completo 15+ plaguicidas
└── report_mida_minsa.pdf              # reporte interpretado

outputs/xai/figures/
├── chlorpyrifos_SR-ARE.svg
├── atrazine_NR-AR.svg
└── ...
```

Formato de `panama_pesticides_profile.csv`:

```
compuesto,familia,CID,SMILES,tarea_critica,prob_max,alerta,NR-AR,...,SR-p53
Clorpirifos,Organofosforado,2730,CCOP(=S)...,SR-ARE,0.85,ALTO RIESGO,0.62,...
```

---

## Entregables

- [ ] `outputs/reports/panama_pesticides_profile.csv` con 15+ plaguicidas
- [ ] `outputs/reports/report_mida_minsa.pdf` para actores no técnicos
- [ ] 6 casos de estudio completos con visualizaciones XAI
- [ ] Comparación predicciones vs datos PPDB documentada
- [ ] `notebooks/07_ghs_validation.ipynb` — tabla de coherencia predicción vs GHS por familia
- [ ] Presentación JIC preparada: narrativa, metodología, 3 casos de estudio, conclusiones

---

## Dependencias

```
torch>=2.0
torch_geometric>=2.4
rdkit>=2023.09      # Draw, MolFromSmiles
pandas, numpy
matplotlib, seaborn
```
