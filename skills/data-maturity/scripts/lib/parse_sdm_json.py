"""Parse a Tableau Next SDM export (JSON or YAML, same key shape) into a NormModel.

Field layout follows the ssot/semantic/models/{sdmName} response documented in
tableau-semantic-authoring/references/api-reference.md: semanticDataObjects[] hold
semanticDimensions/semanticMeasurements; calculatedMeasurements/calculatedDimensions
and semanticMetrics live at the model root.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .normalize import NormField, NormModel, NormObject, NormRelationship

GRAIN_HINTS = ("one row per", "one row =", "grain:")


def _grain_stated(description: str) -> bool:
    text = (description or "").lower()
    return any(hint in text for hint in GRAIN_HINTS)


def _synonyms_of(node: Dict[str, Any]) -> List[str]:
    # Different exports have used "synonyms", "aliases", or nothing at all.
    syns = node.get("synonyms") or node.get("aliases") or []
    if isinstance(syns, str):
        syns = [s.strip() for s in syns.split(",") if s.strip()]
    return list(syns)


def _field_from_table_field(node: Dict[str, Any], obj_name: str, role: str) -> NormField:
    return NormField(
        name=node.get("apiName", ""),
        label=node.get("label", node.get("apiName", "")),
        description=node.get("description"),
        role=role,
        data_type=node.get("dataType", ""),
        aggregation=node.get("aggregationType"),
        is_calculated=False,
        expression=None,
        synonyms=_synonyms_of(node),
        object_name=obj_name,
    )


def _field_from_calc(node: Dict[str, Any], role: str) -> NormField:
    return NormField(
        name=node.get("apiName", ""),
        label=node.get("label", node.get("apiName", "")),
        description=node.get("description"),
        role=role,
        data_type=node.get("dataType", ""),
        aggregation=node.get("aggregationType"),
        is_calculated=True,
        expression=node.get("expression"),
        synonyms=_synonyms_of(node),
        object_name=None,
    )


def parse_sdm_json(data: Dict[str, Any], name: str, fmt: str = "sdm-json") -> NormModel:
    model = NormModel(name=data.get("apiName", name), fmt=fmt)

    for obj in data.get("semanticDataObjects", []) or []:
        obj_name = obj.get("apiName", "")
        description = obj.get("description")
        norm_obj = NormObject(
            name=obj_name,
            label=obj.get("label", obj_name),
            description=description,
            grain_stated=_grain_stated(description or ""),
        )
        for dim in obj.get("semanticDimensions", []) or []:
            norm_obj.fields.append(_field_from_table_field(dim, obj_name, "Dimension"))
        for meas in obj.get("semanticMeasurements", []) or []:
            norm_obj.fields.append(_field_from_table_field(meas, obj_name, "Measure"))
        model.objects.append(norm_obj)

    for calc in data.get("calculatedDimensions", []) or data.get("semanticCalculatedDimensions", []) or []:
        model.calculated_fields.append(_field_from_calc(calc, "Dimension"))
    for calc in data.get("calculatedMeasurements", []) or data.get("semanticCalculatedMeasurements", []) or []:
        model.calculated_fields.append(_field_from_calc(calc, "Measure"))

    for metric in data.get("semanticMetrics", []) or []:
        model.metrics.append(
            {
                "apiName": metric.get("apiName", ""),
                "label": metric.get("label", ""),
                "measurementReference": metric.get("measurementReference"),
                "timeDimensionReference": metric.get("timeDimensionReference"),
                "additionalDimensions": metric.get("additionalDimensions"),
                "description": metric.get("description"),
            }
        )

    for rel in data.get("relationships", []) or []:
        model.relationships.append(
            NormRelationship(
                from_object=rel.get("fromObject", rel.get("from", "")),
                to_object=rel.get("toObject", rel.get("to", "")),
                cardinality=rel.get("cardinality"),
            )
        )

    defaults = data.get("businessPreferences") or data.get("defaults") or {}
    model.defaults = {
        "currency": defaults.get("currency") or defaults.get("defaultCurrency"),
        "fiscal_year_start": defaults.get("fiscalYearStart") or defaults.get("fiscal_year_start"),
        "default_date_field": defaults.get("defaultDateField") or defaults.get("default_date_field"),
    }

    model.synonyms_present = any(f.synonyms for f in model.all_fields()) or any(
        o.description and "synonym" in (o.description or "").lower() for o in model.objects
    )

    if not data.get("semanticDataObjects"):
        model.parse_warnings.append("No semanticDataObjects found — check the export shape.")

    return model
