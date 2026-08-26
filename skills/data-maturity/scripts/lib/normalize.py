"""The normalized model both parsers emit. score.py never sees format differences.

A description counts as present only if it clears TRIVIAL_MIN_LEN and isn't just the
field's own name restated (e.g. "Amount" as the description of `Amount`) — either of
those is noise a customer's export produces for free and would otherwise inflate the
descriptions score without adding anything an agent can use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

TRIVIAL_MIN_LEN = 10


def is_real_description(desc: Optional[str], own_name: Optional[str] = None) -> bool:
    if not desc:
        return False
    text = desc.strip()
    if len(text) < TRIVIAL_MIN_LEN:
        return False
    if own_name and text.lower().replace("_", " ") == own_name.lower().replace("_", " "):
        return False
    return True


@dataclass
class NormField:
    name: str
    label: str = ""
    description: Optional[str] = None
    role: str = "Dimension"  # "Dimension" | "Measure"
    data_type: str = ""
    aggregation: Optional[str] = None
    is_calculated: bool = False
    expression: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    object_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NormObject:
    name: str
    label: str = ""
    description: Optional[str] = None
    grain_stated: bool = False
    fields: List[NormField] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "grain_stated": self.grain_stated,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass
class NormRelationship:
    from_object: str
    to_object: str
    cardinality: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_object,
            "to": self.to_object,
            "cardinality": self.cardinality,
        }


@dataclass
class NormModel:
    name: str
    fmt: str  # "sdm-json" | "tds" | "yaml"
    objects: List[NormObject] = field(default_factory=list)
    calculated_fields: List[NormField] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[NormRelationship] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    synonyms_present: bool = False
    parse_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "format": self.fmt,
            "objects": [o.to_dict() for o in self.objects],
            "calculated_fields": [f.to_dict() for f in self.calculated_fields],
            "metrics": self.metrics,
            "relationships": [r.to_dict() for r in self.relationships],
            "defaults": self.defaults,
            "synonyms_present": self.synonyms_present,
            "parse_warnings": self.parse_warnings,
        }

    def all_fields(self) -> List[NormField]:
        """Every field an agent could reach: table fields + calculated fields."""
        out: List[NormField] = []
        for obj in self.objects:
            out.extend(obj.fields)
        out.extend(self.calculated_fields)
        return out

    def measure_fields(self) -> List[NormField]:
        return [f for f in self.all_fields() if f.role == "Measure"]
