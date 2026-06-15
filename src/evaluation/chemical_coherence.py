"""
Validación química de las explicaciones XAI.

Comprueba si los átomos que el modelo marca como "importantes"
pertenecen a grupos funcionales con toxicidad documentada.

Por ejemplo: si el modelo dice que el átomo de fósforo es importante
para la predicción de estrés oxidativo (SR-ARE), eso es coherente
porque el grupo fosforotioato (P=S) causa estrés oxidativo.

Métrica principal: Precision@k
  "De los k átomos más importantes según XAI,
   ¿cuántos pertenecen a un grupo funcional tóxico conocido?"
"""

from __future__ import annotations

import numpy as np
from rdkit.Chem import MolFromSmarts, MolFromSmiles

# Patrones SMARTS específicos por vía de toxicidad.
# Cada patrón representa un grupo funcional con mecanismo documentado.
# Se usan patrones MÁS ESPECÍFICOS que los genéricos para evitar
# falsos positivos (ej: [P](=S)(O)(O) en vez de solo [Cl]).
TOXIC_GROUPS: dict[str, list[str]] = {
    # Receptor de andrógenos: esteroides sintéticos, ésteres fenólicos
    "NR-AR": [
        "[#6]1(=O)[#6][#6][#6][#6][#6]1",  # ciclohexanona (núcleo esteroidal)
        "c1ccc(O)cc1",  # fenol (mimetiza estradiol)
        "[#6]-[#6](=O)-[#8]-[#6]",  # éster carboxílico
    ],
    "NR-AR-LBD": [
        "[#6]1(=O)[#6][#6][#6][#6][#6]1",
        "c1ccc(O)cc1",
        "[F,Cl,Br]-c1ccccc1",  # halobenceno
    ],
    # Receptor aril-hidrocarburo: aromáticos policíclicos planos
    "NR-AhR": [
        "c1ccc2ccccc2c1",  # naftaleno (2 anillos fusionados)
        "c1ccnc2ccccc12",  # quinolina
        "c1ccc2[nH]ccc2c1",  # indol
        "c1ccc2occc2c1",  # benzofurano
    ],
    # Aromatasa: azoles (inhiben CYP450) y halogenados
    "NR-Aromatase": [
        "n1ccnc1",  # imidazol
        "n1cncn1",  # triazol (tebuconazol, propiconazol)
        "c1ccncc1",  # piridina
        "[Cl]c1nccnn1",  # clorotriazina (atrazina)
    ],
    # Receptor de estrógenos: fenoles, bisfenoles, difenilos
    "NR-ER": [
        "c1ccc(O)cc1",  # fenol
        "c1ccc(-c2ccc(O)cc2)cc1",  # bisfenol
        "c1ccc(-c2ccccc2)cc1",  # bifenilo
    ],
    "NR-ER-LBD": [
        "c1ccc(O)cc1",
        "c1ccc(-c2ccc(O)cc2)cc1",
        "[OH]-c1cc([#6])ccc1",  # fenol sustituido
    ],
    # PPAR-gamma: ácidos grasos, tiazolidindionas
    "NR-PPAR-gamma": [
        "C(=O)[OH]",  # ácido carboxílico
        "[#6]C(=O)Nc1ccccc1",  # amida aromática
        "CCCCCC",  # cadena alifática larga (≥6 carbonos)
    ],
    # Estrés oxidativo (Nrf2/ARE): electrófilos, fosforotioatos
    "SR-ARE": [
        "[P](=S)([O,S])([O,S])",  # fosforotioato (clorpirifos, malatión)
        "[N+](=O)[O-]",  # grupo nitro
        "[P](=O)([OH])([NH])",  # fosfonato + amina (glifosato)
    ],
    # Daño al ADN mitocondrial: agentes alquilantes, epóxidos
    "SR-AtAD5": [
        "[N+](=O)[O-]",  # grupo nitro (genotóxico)
        "C1OC1",  # epóxido
        "[Cl,Br]-[#6]=[#6]",  # haluro vinílico
    ],
    # Estrés por calor: compuestos aromáticos lipofílicos
    "SR-HSE": [
        "C(=O)[O]C(=O)",  # anhídrido
        "c1cc([#6](=O))ccc1",  # acetofenona y derivados
        "[P](=O)([O])([O])",  # fosforato (organofosforados)
    ],
    # Potencial de membrana mitocondrial: desacopladores, lipofílicos
    "SR-MMP": [
        "[P](=S)([O,S])([O,S])",  # fosforotioato
        "c1ccc([N+](=O)[O-])cc1",  # nitrobenceno
        "[F,Cl,Br,I]-c1ccccc1",  # halobenceno
    ],
    # Vía p53 (daño al ADN): agentes alquilantes, intercalantes
    "SR-p53": [
        "[N+](=O)[O-]",  # grupo nitro (mutagénico)
        "C1OC1",  # epóxido (alquilante)
        "[Cl]-[#6]=[#6]",  # haluro vinílico
        "c1ccc2ccccc2c1",  # policíclico (intercalante)
    ],
}


def precision_at_k(
    smiles: str,
    node_importance: np.ndarray,
    task_name: str,
    k: int = 3,
) -> int:
    """
    Verifica si al menos uno de los k átomos más importantes
    pertenece a un grupo funcional tóxico conocido para esta tarea.

    Args:
        smiles: SMILES de la molécula
        node_importance: importancia por átomo (de GNNExplainer o Grad-CAM)
        task_name: nombre de la tarea Tox21 (ej: "SR-ARE")
        k: cuántos átomos top considerar

    Returns:
        1 si al menos un átomo top-k está en un grupo tóxico conocido, 0 si no
    """
    mol = MolFromSmiles(smiles)
    if mol is None:
        return 0

    # Obtener los k átomos con mayor importancia
    top_k_atoms = set(np.argsort(node_importance)[-k:].tolist())

    # Buscar si alguno cae en un patrón SMARTS conocido para esta tarea
    expected = TOXIC_GROUPS.get(task_name, [])
    for pattern in expected:
        query = MolFromSmarts(pattern)
        if query is None:
            continue
        matches = mol.GetSubstructMatches(query)
        matched_atoms = {a for match in matches for a in match}
        if matched_atoms & top_k_atoms:
            return 1
    return 0
