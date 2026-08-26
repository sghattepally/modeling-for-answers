"""Parse a classic Tableau published data source (.tds or .tdsx) into a NormModel.

.tdsx is a zip containing one top-level .tds (plus extracts we don't care about);
.tds is XML: <datasource> holds <column> nodes with caption/role/datatype, an
optional child <calculation formula=...> for computed fields, and an optional
<desc> for the description. Classic PDS metadata has no notion of calculated
dimensions/measurements as first-class objects (they're just columns with a
<calculation>), no semantic metrics, and no synonyms API — those all legitimately
score near zero, which is the intended signal per the plan.
"""

from __future__ import annotations

import zipfile
from typing import Optional
from xml.etree import ElementTree as ET

from .normalize import NormField, NormModel, NormObject

ROLE_MAP = {"dimension": "Dimension", "measure": "Measure"}


def _extract_tds_bytes(path: str) -> bytes:
    if path.lower().endswith(".tdsx"):
        with zipfile.ZipFile(path) as zf:
            tds_names = [n for n in zf.namelist() if n.lower().endswith(".tds")]
            if not tds_names:
                raise ValueError(f"No .tds file found inside {path}")
            return zf.read(tds_names[0])
    with open(path, "rb") as fh:
        return fh.read()


def _col_description(col: ET.Element) -> Optional[str]:
    desc_el = col.find("desc")
    if desc_el is None:
        return None
    # Tableau nests description text under <desc><formatted-text><run>text</run>...
    text = "".join(desc_el.itertext()).strip()
    return text or None


def parse_tds(path: str, name: str) -> NormModel:
    raw = _extract_tds_bytes(path)
    fmt = "tds"
    model = NormModel(name=name, fmt=fmt)

    root = ET.fromstring(raw)
    datasources = root.findall(".//datasource")
    if root.tag == "datasource":
        datasources = [root]

    if not datasources:
        model.parse_warnings.append("No <datasource> element found in TDS XML.")
        return model

    for ds in datasources:
        caption = ds.get("caption") or name
        obj = NormObject(name=caption, label=caption, description=None, grain_stated=False)

        for col in ds.findall(".//column"):
            calc_el = col.find("calculation")
            is_calculated = calc_el is not None
            expression = calc_el.get("formula") if calc_el is not None else None

            role = ROLE_MAP.get((col.get("role") or "").lower(), "Dimension")
            fld = NormField(
                name=col.get("name", ""),
                label=col.get("caption", col.get("name", "")),
                description=_col_description(col),
                role=role,
                data_type=col.get("datatype", ""),
                aggregation=col.get("default-aggregation"),
                is_calculated=is_calculated,
                expression=expression,
                synonyms=[],  # classic PDS metadata has no synonym concept
                object_name=caption,
            )
            if is_calculated:
                model.calculated_fields.append(fld)
            else:
                obj.fields.append(fld)

        model.objects.append(obj)

    # Classic PDS: no metrics API, no business-preferences block, no synonyms.
    model.metrics = []
    model.defaults = {"currency": None, "fiscal_year_start": None, "default_date_field": None}
    model.synonyms_present = False
    model.parse_warnings.append(
        "Classic PDS format has no governed-metrics, synonyms, or business-preferences "
        "concept — those dimensions score as absent by construction, not as a parse failure."
    )

    return model


def is_tds_path(path: str) -> bool:
    return path.lower().endswith((".tds", ".tdsx"))
