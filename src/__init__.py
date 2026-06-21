"""GNN-GIN + XAI para predicción de toxicidad de plaguicidas (Tox21 / corpus Panamá).

Submódulos:
    data         — featurización SMILES→grafo, dataset PyG, splits scaffold
    models       — GIN principal + baselines (RF, MLP, SMILES2vec)
    training     — loop de entrenamiento, scheduler, pérdida enmascarada
    xai          — GNNExplainer, Grad-CAM y visualización molecular
    evaluation   — métricas multitarea, validación cruzada, coherencia química
    analisis_proyecto — pipeline ChEMBL (Flujo B) para la parte de analítica del curso
"""

__version__ = "0.1.0"
