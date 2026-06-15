# Fase V — Aplicación a Plaguicidas de Panamá

## 1. Contexto: por qué plaguicidas en Panamá

Panamá es un país con agricultura de exportación intensiva (banano, café, caña de azúcar, piña). Los plaguicidas son esenciales para la producción pero su uso inadecuado tiene consecuencias para la salud humana y los ecosistemas.

### Actores institucionales

| Institución | Rol | Qué necesita |
|---|---|---|
| **MIDA** (Ministerio de Desarrollo Agropecuario) | Registra y autoriza plaguicidas | Herramientas para evaluar toxicidad de nuevos productos |
| **MINSA** (Ministerio de Salud) | Regula exposición humana | Perfiles de riesgo por vía de toxicidad |
| **Productores agrícolas** | Usan los plaguicidas | Alternativas menos tóxicas con eficacia similar |

### El problema actual
La evaluación toxicológica de un plaguicida requiere ensayos costosos y lentos. Este proyecto propone usar **predicción computacional** como herramienta de priorización: identificar rápidamente qué compuestos merecen una evaluación experimental más profunda.

---

## 2. El corpus de plaguicidas panameños

### Ingredientes activos incluidos

Seleccionamos 20 ingredientes activos registrados en el MIDA que representan las principales familias químicas usadas en Panamá:

#### Organofosforados (inhibidores de acetilcolinesterasa)

| Compuesto | Uso principal | Cultivos |
|---|---|---|
| **Clorpirifos** | Insecticida de amplio espectro | Banano, piña, arroz |
| **Malatión** | Insecticida, control de mosquitos | Urbano, hortalizas |
| **Dimetoato** | Insecticida sistémico | Hortalizas, frutales |
| **Metil paratión** | Insecticida (muy tóxico) | Algodón, arroz |

#### Carbamatos (inhibidores de acetilcolinesterasa)

| Compuesto | Uso principal | Cultivos |
|---|---|---|
| **Carbaril** | Insecticida | Frutales, ornamentales |
| **Metomil** | Insecticida | Tabaco, hortalizas |
| **Aldicarb** | Insecticida/nematicida | Banano, papa |

#### Triazinas (inhibidores de fotosíntesis)

| Compuesto | Uso principal | Cultivos |
|---|---|---|
| **Atrazina** | Herbicida | Caña de azúcar, maíz |
| **Simazina** | Herbicida | Frutales, viñedos |

#### Fungicidas azólicos (inhibidores de CYP450)

| Compuesto | Uso principal | Cultivos |
|---|---|---|
| **Tebuconazol** | Fungicida sistémico | Banano, cereales |
| **Propiconazol** | Fungicida | Cereales, banano |
| **Difenoconazol** | Fungicida | Hortalizas, frutales |

#### Piretroides (moduladores de canales de sodio)

| Compuesto | Uso principal | Cultivos |
|---|---|---|
| **Cipermetrina** | Insecticida | Algodón, hortalizas |
| **Deltametrina** | Insecticida | Cultivos varios |
| **Lambda-cihalotrina** | Insecticida | Cultivos varios |

#### Otros

| Compuesto | Tipo | Uso principal |
|---|---|---|
| **Glifosato** | Herbicida (inhibidor de EPSP sintasa) | Cultivos transgénicos, control general |
| **Paraquat** | Herbicida (generador de radicales) | Desecante, control general |
| **2,4-D** | Herbicida auxínico | Pastizales, cereales |
| **Mancozeb** | Fungicida ditiocarbamato | Banano, papa, tomate |
| **Clorotalonil** | Fungicida multiusos | Banano, tomate, papa |

### Fuentes de datos

Los datos se obtienen de **PubChem** (base de datos pública del NIH) para garantizar trazabilidad y reproducibilidad:

1. **PubChem Compound**: SMILES canónico verificado por el NIH
2. **PubChem Classification (HID 72)**: taxonomía de plaguicidas por familia
3. **PubChem Hazard (GHS)**: etiquetas de peligro según el Sistema Globalmente Armonizado

---

## 3. Pipeline de aplicación

### Paso 1: Construir el corpus

```bash
python -c "from src.data.pubchem_api import build_full_panama_corpus; build_full_panama_corpus()"
```

Esto ejecuta:
1. Busca cada ingrediente activo por nombre → obtiene CID y SMILES
2. Descarga familias completas del árbol de clasificación HID 72
3. Enriquece CIDs sin SMILES consultando PubChem Compound en lotes
4. Valida y canonicaliza todos los SMILES con RDKit
5. Descarga etiquetas GHS para validación posterior

### Paso 2: Predicción con el modelo GNN-GIN

Para cada plaguicida:
1. Convertir SMILES → grafo molecular (con `featurizer.py`)
2. Pasar el grafo por el modelo entrenado
3. Obtener 12 probabilidades de toxicidad (una por diana biológica)
4. Clasificar el riesgo:
   - **Alto riesgo**: probabilidad > 0.7
   - **Riesgo moderado**: probabilidad 0.4 - 0.7
   - **Bajo riesgo**: probabilidad < 0.4

### Paso 3: Explicación XAI

Para la tarea con mayor probabilidad de toxicidad:
1. Ejecutar GNNExplainer → identificar átomos clave
2. Ejecutar Grad-CAM → corroborar con método alternativo
3. Generar imagen SVG con molécula coloreada
4. Mapear átomos importantes a grupos funcionales

### Paso 4: Validación contra datos experimentales

Comparar las predicciones del modelo con:
- **Etiquetas GHS de PubChem**: H300-H412 (peligros regulatorios)
- **PPDB** (Pesticide Properties DataBase): datos experimentales de toxicidad
- **Literatura científica**: mecanismos de acción documentados

---

## 4. Casos de estudio prioritarios

### Caso 1: Clorpirifos (Organofosforado)

**¿Por qué es prioritario?** Es el insecticida más usado en el cultivo de banano en Panamá. Prohibido en la UE desde 2020 por neurotoxicidad.

```
SMILES: CCOP(=S)(OCC)Oc1cc(Cl)c(Cl)cc1Cl
Familia: Organofosforado
Mecanismo: Inhibe acetilcolinesterasa; el grupo P=S se bioactiva a P=O en el hígado
```

**Predicción esperada:**
- **SR-ARE** (estrés oxidativo): ALTO — el metabolismo del grupo fosforotioato genera radicales
- **NR-AhR** (receptor AhR): ALTO — el anillo triclorobenceno activa AhR
- **SR-MMP** (mitocondria): MODERADO — los organofosforados afectan la cadena respiratoria

**Grupo funcional clave:** El fósforo (P) y el azufre (S=) del grupo fosforotioato.

**Validación GHS esperada:** H301 (tóxico por ingestión), H311 (tóxico por contacto), H410 (muy tóxico para vida acuática).

### Caso 2: Atrazina (Triazina)

**¿Por qué es prioritario?** Herbicida ampliamente usado en caña de azúcar. Es un disruptor endocrino conocido — causa feminización en anfibios.

```
SMILES: CCNc1nc(Cl)nc(NC(C)C)n1
Familia: Triazina
Mecanismo: Inhibe fotosíntesis (plantas); en animales, induce aromatasa → exceso de estrógeno
```

**Predicción esperada:**
- **NR-AR** (andrógenos): ALTO — interfiere con señalización androgénica
- **NR-ER** (estrógenos): ALTO — induce producción de estrógeno vía aromatasa
- **NR-Aromatase**: MODERADO — induce (no inhibe) aromatasa

**Grupo funcional clave:** El anillo triazina con el cloro.

### Caso 3: Tebuconazol (Azol)

**¿Por qué es prioritario?** Fungicida sistémico usado en banano. Los azoles inhiben enzimas CYP450 humanas además de las fúngicas.

```
SMILES: OC(Cn1cncn1)(c1ccc(Cl)cc1)C(C)(C)C
Familia: Triazol
Mecanismo: El anillo triazol coordina con el hierro del grupo hemo de CYP450
```

**Predicción esperada:**
- **NR-Aromatase**: ALTO — inhibe CYP19 (aromatasa es un CYP450)
- **NR-PPAR-gamma**: MODERADO — los azoles afectan metabolismo lipídico

**Grupo funcional clave:** El anillo triazol (n1cncn1) y el cloro del fenilo.

### Caso 4: Cipermetrina (Piretroide)

```
SMILES: CC1(C)C(C=C(Cl)Cl)C1C(=O)OC(C#N)c1cccc(Oc2ccccc2)c1
Familia: Piretroide sintético
Mecanismo: Modula canales de sodio → hiperexcitación nerviosa
```

**Predicción esperada:**
- **SR-HSE** (estrés por calor): ALTO — la hiperexcitación desnaturaliza proteínas
- **SR-MMP** (mitocondria): MODERADO — afecta la cadena de transporte electrónico

### Caso 5: Paraquat (Herbicida bipiridilos)

```
SMILES: C[n+]1ccc(-c2cc[n+](C)cc2)cc1
Familia: Bipiridilos
Mecanismo: Genera superóxido (O₂⁻) por ciclo redox → destrucción celular masiva
```

**Predicción esperada:**
- **SR-ARE** (estrés oxidativo): MUY ALTO — mecanismo principal
- **SR-p53** (daño al ADN): ALTO — los radicales dañan directamente el ADN

### Caso 6: Glifosato (Aminoácido fosfonato)

```
SMILES: OC(=O)CNCP(O)(O)=O
Familia: Fosfonatos
Mecanismo: Inhibe EPSP sintasa (ruta del shikimato, solo en plantas)
```

**Predicción esperada:**
- **SR-ARE** (estrés oxidativo): MODERADO — controversia actual en la literatura
- El modelo debería dar probabilidades **bajas** en las demás vías

---

## 5. Validación con etiquetas GHS

El Sistema Globalmente Armonizado (GHS) clasifica los peligros químicos con códigos H:

### Correlaciones esperadas predicción vs GHS

| Código GHS | Significado | Tarea Tox21 correlacionada |
|---|---|---|
| H300/H301/H302 | Fatal/tóxico/nocivo por ingestión | SR-ARE, SR-MMP |
| H310/H311/H312 | Fatal/tóxico/nocivo por contacto | SR-HSE |
| H330/H331 | Fatal/tóxico por inhalación | SR-ARE |
| H340/H341 | Mutagénico | SR-p53, SR-AtAD5 |
| H350/H351 | Carcinogénico | SR-p53 |
| H360/H361 | Tóxico para la reproducción | NR-AR, NR-ER |
| H400/H410 | Muy tóxico para vida acuática | Múltiples |

Para cada plaguicida, verificar si:
- Predicción alta en NR-AR/NR-ER ↔ H360/H361 documentado
- Predicción alta en SR-p53/SR-AtAD5 ↔ H340/H350 documentado
- Predicción alta en SR-ARE ↔ H300/H301/H330 documentado

---

## 6. Reporte institucional

Para cada compuesto, generar un perfil que incluya:

1. **Datos de identificación**: nombre, SMILES, familia, registro MIDA
2. **Tabla de predicciones**: 12 probabilidades con nivel de riesgo
3. **Imagen XAI**: molécula coloreada con átomos clave señalados
4. **Interpretación química**: qué grupo funcional causa la toxicidad y por qué
5. **Comparación experimental**: predicción vs datos de PPDB y etiquetas GHS
6. **Recomendaciones**: basadas en el perfil de toxicidad

### Formato del reporte

El reporte final (`outputs/reports/report_mida_minsa.pdf`) está diseñado para **actores no técnicos**: usa lenguaje claro, visualizaciones intuitivas (rojo = peligro, verde = seguro), y explica cada predicción en términos de riesgo para la salud humana y ambiental.

---

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/data/pubchem_api.py` | Descarga corpus panameño desde PubChem |
| `src/xai/gnn_explainer.py` | Explicaciones por molécula |
| `src/xai/grad_cam.py` | Explicaciones alternativas |
| `src/xai/visualizer.py` | Imágenes SVG coloreadas |
| `src/evaluation/chemical_coherence.py` | Validación SMARTS |

## Ejecución

```bash
# 1. Construir corpus panameño
python -c "from src.data.pubchem_api import build_full_panama_corpus; build_full_panama_corpus()"

# 2. Generar predicciones + explicaciones (requiere modelo entrenado)
python scripts/explain_panama.py --model outputs/models/best_gin_model.pt

# 3. Validar contra GHS
python scripts/validate_ghs.py --predictions outputs/results/panama_predictions.csv \
                                --ghs data/raw/pubchem_ghs_labels.csv
```
