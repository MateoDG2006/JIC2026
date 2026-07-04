#!/usr/bin/env python
"""Verificación end-to-end del pipeline Opción A (Fases 2–4)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.modeling.baseline import (  # noqa: E402
    CompoundLevelBaseline,
    RowLevelSplitContrast,
)
from src.analisis_proyecto.modeling.multivariate import (  # noqa: E402
    MULTIVARIATE_FEATURE_COLS,
    MultivariateAnalyzer,
)
from src.analisis_proyecto.preprocessing.pipeline import (  # noqa: E402
    ChemblPreprocessor,
    FEATURE_COLS,
    load_bioactivity,
)


@dataclass
class FlowBPaths:
    root: Path

    @property
    def raw_csv(self) -> Path:
        return self.root / "data" / "raw" / "chembl_panama_bioactivity.csv"

    @property
    def activities_csv(self) -> Path:
        return self.root / "data" / "processed" / "activities_clean.csv"

    @property
    def compounds_csv(self) -> Path:
        return self.root / "data" / "processed" / "compounds_features.csv"

    @property
    def stats_csv(self) -> Path:
        return self.root / "outputs" / "chembl" / "results" / "stats_tests.csv"

    @property
    def stats_exploratory_csv(self) -> Path:
        return self.root / "outputs" / "chembl" / "results" / "stats_tests_exploratory.csv"

    @property
    def cluster_json(self) -> Path:
        return self.root / "outputs" / "chembl" / "results" / "clustering_summary.json"

    @property
    def baseline_csv(self) -> Path:
        return self.root / "outputs" / "chembl" / "results" / "baseline_honest_metrics.csv"


class FlowBPipeline:
    """Orquesta limpieza, agregación, multivariado y baseline P6."""

    NAN_THRESHOLD = 250
    EXPECTED_COMPOUNDS = 107

    def __init__(self, paths: FlowBPaths | None = None) -> None:
        self.paths = paths or FlowBPaths(ROOT)
        self.preprocessor = ChemblPreprocessor(nan_threshold=self.NAN_THRESHOLD)
        self.multivariate = MultivariateAnalyzer()

    def run(self, df: pd.DataFrame) -> None:
        activities = self.preprocessor.clean_activities(df)
        self.paths.activities_csv.parent.mkdir(parents=True, exist_ok=True)
        activities.to_csv(self.paths.activities_csv, index=False)

        compounds = self.preprocessor.build_compound_features(activities)
        assert compounds["chembl_id"].nunique() == len(compounds)
        assert len(compounds) == self.EXPECTED_COMPOUNDS, (
            f"Esperado {self.EXPECTED_COMPOUNDS} compuestos, got {len(compounds)}"
        )

        desc_cols = [c for c in FEATURE_COLS + ["heavy_atoms"] if c in compounds.columns]
        assert compounds[desc_cols].isna().sum().sum() == 0, "NaN en descriptores"

        mv = self.multivariate.analyze(compounds)
        assert "num_ro5_violations" not in mv.summary["features_used"]
        assert mv.summary.get("features_dropped") == ["num_ro5_violations"]

        compounds["cluster"] = mv.kmeans_labels
        compounds["cluster_label"] = mv.summary["cluster_validity_note"]
        compounds.to_csv(self.paths.compounds_csv, index=False)

        self.paths.stats_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(mv.stats_rows).to_csv(self.paths.stats_csv, index=False)
        pd.DataFrame(mv.exploratory_stats_rows).to_csv(
            self.paths.stats_exploratory_csv, index=False
        )
        self.paths.cluster_json.write_text(json.dumps(mv.summary, indent=2), encoding="utf-8")

        row_contrast = RowLevelSplitContrast().evaluate(activities)
        compound_view = CompoundLevelBaseline().evaluate(compounds)
        baseline = pd.DataFrame([m.to_dict() for m in row_contrast + [compound_view]])
        baseline.to_csv(self.paths.baseline_csv, index=False)

        leak = baseline[baseline["split"] == "filas_KFold_CON_FUGA"].iloc[0]
        honest = baseline[baseline["split"] == "filas_GroupKFold_HONESTO"].iloc[0]
        assert leak["n"] == honest["n"], "Contraste filas: target y n deben coincidir"

        imp = self.preprocessor.imputation_report(activities)
        print(f"  activities: {activities.shape} | compounds: {compounds.shape}")
        print(f"  pChEMBL imputados: {imp['pct_imputed']}%")
        print(f"  features multivariado: {mv.summary['features_used']}")
        print(f"  dropped: {mv.summary['features_dropped']}")
        print(f"  PCA var PC1+PC2: {mv.summary['pca_var_explained'] * 100:.1f}%")
        print(f"  best_k={mv.summary['best_k']} | ARI={mv.summary['ari_vs_family']:.3f}")
        print(
            f"  baseline filas (fuga): R²={leak['r2_cv_mean']:.3f} ± {leak['r2_cv_std']:.3f} (n={leak['n']})"
        )
        print(
            f"  baseline filas (honesto): R²={honest['r2_cv_mean']:.3f} ± {honest['r2_cv_std']:.3f}"
        )
        print(
            f"  baseline compuesto: R²={compound_view.r2_cv_mean:.3f} ± {compound_view.r2_cv_std:.3f}"
        )


def main() -> int:
    paths = FlowBPaths(ROOT)
    if not paths.raw_csv.exists():
        print(f"ERROR: falta {paths.raw_csv}")
        return 1

    print(f"Usando dataset real: {paths.raw_csv}")
    FlowBPipeline(paths).run(load_bioactivity(paths.raw_csv))
    print("=== verify_flow_b OK (Opción A) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
