"""Modelos tipados del pipeline ChEMBL — reemplazan dicts de mapeo ad hoc."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, ClassVar, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self
else:
    Self = Any  # Python 3.10 compat

import pandas as pd

from src.analisis_proyecto.core.constants import (
    bioactivity_columns,
    mida_registry_entries,
    pchembl_active_threshold,
    standard_types_expanded,
    standard_types_narrow,
    units_to_molar,
)


class MatchStatus(str, Enum):
    OK = "ok"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


class StandardActivityTypes:
    """Conjuntos de standard_type soportados por ChEMBL (``config/chembl/standard_types.json``)."""

    NARROW: ClassVar[tuple[str, ...]] = standard_types_narrow()
    EXPANDED: ClassVar[tuple[str, ...]] = standard_types_expanded()
    DEFAULT: ClassVar[tuple[str, ...]] = EXPANDED

    @classmethod
    def resolve(cls, raw: Any) -> tuple[str, ...]:
        if raw == "narrow":
            return cls.NARROW
        if isinstance(raw, (list, tuple)) and raw:
            return tuple(str(t) for t in raw)
        return cls.DEFAULT


@dataclass(frozen=True)
class MidaEntry:
    name: str
    chembl_id: str
    family: str


class MidaRegistry:
    """Registro curado MIDA → ChEMBL ID + familia química (``config/chembl/mida_registry.json``)."""

    _ENTRIES: ClassVar[tuple[MidaEntry, ...]] = tuple(
        MidaEntry(e["name"], e["chembl_id"], e["family"]) for e in mida_registry_entries()
    )

    def __init__(self) -> None:
        self._by_name = {e.name: e for e in self._ENTRIES}

    def chembl_id(self, compound_name: str) -> str | None:
        entry = self._by_name.get(compound_name)
        return entry.chembl_id if entry else None

    def family(self, compound_name: str) -> str:
        entry = self._by_name.get(compound_name)
        return entry.family if entry else "unknown"

    def contains(self, compound_name: str) -> bool:
        return compound_name in self._by_name

    def __iter__(self) -> Iterator[MidaEntry]:
        return iter(self._ENTRIES)


@dataclass
class CorpusCompound:
    compound_name: str
    pubchem_cid: int | str
    smiles: str
    family: str
    source: str = "unknown"
    is_mida: bool = False

    @property
    def mapping_key(self) -> str:
        return str(self.pubchem_cid)

    @classmethod
    def from_row(cls, row: pd.Series | dict[str, Any]) -> Self:
        data = row.to_dict() if isinstance(row, pd.Series) else row
        return cls(
            compound_name=str(data["compound_name"]),
            pubchem_cid=data["pubchem_cid"],
            smiles=str(data.get("smiles", "")),
            family=str(data.get("family", "unknown")),
            source=str(data.get("source", "unknown")),
            is_mida=bool(data.get("is_mida", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChemblMatch:
    chembl_id: str | None
    match_method: str | None
    match_status: MatchStatus | str
    n_candidates: int
    chembl_pref_name: str | None = None

    @classmethod
    def found(
        cls,
        chembl_id: str,
        method: str,
        *,
        ambiguous: bool = False,
        n_candidates: int = 1,
        pref_name: str | None = None,
    ) -> Self:
        return cls(
            chembl_id=chembl_id,
            match_method=method,
            match_status=MatchStatus.AMBIGUOUS if ambiguous else MatchStatus.OK,
            n_candidates=n_candidates,
            chembl_pref_name=pref_name,
        )

    @classmethod
    def not_found(cls) -> Self:
        return cls(
            chembl_id=None,
            match_method=None,
            match_status=MatchStatus.NOT_FOUND,
            n_candidates=0,
            chembl_pref_name=None,
        )

    def to_dict(self) -> dict[str, Any]:
        status = self.match_status.value if isinstance(self.match_status, MatchStatus) else self.match_status
        return {
            "chembl_id": self.chembl_id,
            "match_method": self.match_method,
            "match_status": status,
            "n_candidates": self.n_candidates,
            "chembl_pref_name": self.chembl_pref_name,
        }


@dataclass
class MappingRecord:
    compound: CorpusCompound
    match: ChemblMatch

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.compound.to_dict(),
            **self.match.to_dict(),
        }


@dataclass
class MolecularProperties:
    mw_freebase: float | None = None
    alogp: float | None = None
    psa: float | None = None
    hba: int | None = None
    hbd: int | None = None
    num_ro5_violations: int | None = None
    aromatic_rings: int | None = None
    heavy_atoms: int | None = None
    rtb: int | None = None
    molecular_species: str | None = None
    cx_logp: float | None = None
    cx_logd: float | None = None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityFilterConfig:
    impute_pchembl: bool = True
    require_exact_relation: bool = True
    exclude_validity_comment: bool = True

    @classmethod
    def from_mapping(cls, data: dict[str, bool] | None) -> Self:
        defaults = cls()
        if not data:
            return defaults
        return cls(
            impute_pchembl=bool(data.get("impute_pchembl", defaults.impute_pchembl)),
            require_exact_relation=bool(data.get("require_exact_relation", defaults.require_exact_relation)),
            exclude_validity_comment=bool(data.get("exclude_validity_comment", defaults.exclude_validity_comment)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "impute_pchembl": self.impute_pchembl,
            "require_exact_relation": self.require_exact_relation,
            "exclude_validity_comment": self.exclude_validity_comment,
        }


@dataclass
class ChemblConfig:
    version: str = "37"
    server_url: str = "http://127.0.0.1:8765"
    ftp_url: str = (
        "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_37_sqlite.tar.gz"
    )
    pchembl_active_threshold: float = pchembl_active_threshold()
    standard_types: tuple[str, ...] = StandardActivityTypes.DEFAULT
    quality_filters: QualityFilterConfig = field(default_factory=QualityFilterConfig)

    def require_server_url(self) -> str:
        url = (self.server_url or "").strip()
        if not url:
            raise ValueError("chembl.server_url es obligatorio (make chembl-server-up)")
        return url.rstrip("/")

    def standard_types_tuple(self) -> tuple[str, ...]:
        return self.standard_types

    def quality_filters_dict(self) -> dict[str, bool]:
        return self.quality_filters.as_dict()

    @classmethod
    def from_yaml_section(cls, section: dict[str, Any] | None) -> Self:
        section = section or {}
        return cls(
            version=str(section.get("version", "37")),
            server_url=str(section.get("server_url", "http://127.0.0.1:8765")),
            ftp_url=str(section.get(
                "ftp_url",
                "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_37_sqlite.tar.gz",
            )),
            pchembl_active_threshold=float(section.get("pchembl_active_threshold", 6.0)),
            standard_types=StandardActivityTypes.resolve(section.get("standard_types")),
            quality_filters=QualityFilterConfig.from_mapping(section.get("quality_filters")),
        )


class BioactivitySchema:
    """Columnas del dataset largo de bioactividad (``config/chembl/columns.json``)."""

    COLUMNS: ClassVar[tuple[str, ...]] = bioactivity_columns()

    @classmethod
    def empty_frame(cls) -> pd.DataFrame:
        return pd.DataFrame(columns=list(cls.COLUMNS))


class ConcentrationUnits:
    """Conversión de unidades ChEMBL → molar para pChEMBL (``config/chembl/concentration_units.json``)."""

    TO_MOLAR: ClassVar[dict[str, float]] = units_to_molar()

    @classmethod
    def molar_factor(cls, units: str | None) -> float | None:
        if not units:
            return None
        return cls.TO_MOLAR.get(str(units).strip().lower())
