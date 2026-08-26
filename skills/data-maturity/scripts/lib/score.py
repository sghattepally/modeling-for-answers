"""Rubric engine: scores a NormModel across six weighted dimensions.

Thresholds and weights mirror references/maturity-rubric.md — if you change a number
here, change it there too. Each dimension returns (score 0-100, findings). Findings
are dicts: {"severity": "red"|"yellow"|"green", "message": str, "location": str}.
"""

from __future__ import annotations

import difflib
from typing import Dict, List, Tuple

from .normalize import NormModel, is_real_description

WEIGHTS = {
    "structural": 0.25,
    "descriptions": 0.25,
    "synonyms": 0.15,
    "metrics": 0.20,
    "defaults": 0.10,
    "degrade": 0.05,
}

LEVEL_BANDS = [
    (85, "L5", "Agent-ready"),
    (70, "L4", "Governed"),
    (50, "L3", "Emerging"),
    (30, "L2", "Basic"),
    (0, "L1", "Ad-hoc"),
]

DEGRADE_KEYWORDS = (
    "unknown member",
    "no data",
    "no opportunities",
    "no orders",
    "not present",
    "absence",
    "declines",
    "no quota",
)


def _sev(score: float) -> str:
    if score >= 75:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


def _band(score: float) -> Tuple[str, str]:
    for threshold, code, label in LEVEL_BANDS:
        if score >= threshold:
            return code, label
    return "L1", "Ad-hoc"


def _find_cycle(model: NormModel) -> List[str]:
    graph: Dict[str, List[str]] = {}
    for rel in model.relationships:
        graph.setdefault(rel.from_object, []).append(rel.to_object)

    visiting, visited = set(), set()

    def dfs(node: str, path: List[str]) -> List[str]:
        if node in visiting:
            return path + [node]
        if node in visited:
            return []
        visiting.add(node)
        for neighbor in graph.get(node, []):
            result = dfs(neighbor, path + [node])
            if result:
                return result
        visiting.discard(node)
        visited.add(node)
        return []

    for start in list(graph):
        cycle = dfs(start, [])
        if cycle:
            return cycle
    return []


def _look_alike_pairs(model: NormModel) -> List[Tuple[str, str]]:
    measures = model.measure_fields()
    pairs: List[Tuple[str, str]] = []
    for i, a in enumerate(measures):
        for b in measures[i + 1 :]:
            similarity = difflib.SequenceMatcher(None, a.label.lower(), b.label.lower()).ratio()
            if similarity < 0.55:
                continue
            a_ok = is_real_description(a.description, a.label)
            b_ok = is_real_description(b.description, b.label)
            if not (a_ok and b_ok):
                pairs.append((a.label or a.name, b.label or b.name))
    return pairs


def score_structural(model: NormModel) -> Tuple[float, List[dict]]:
    findings: List[dict] = []
    score = 100.0

    cycle = _find_cycle(model)
    if cycle:
        score -= 60
        findings.append(
            {
                "severity": "red",
                "message": f"Circular reference in relationships: {' -> '.join(cycle)}",
                "location": "relationships",
            }
        )

    undeclared = [r for r in model.relationships if not r.cardinality]
    if undeclared and model.relationships:
        penalty = min(25, 5 * len(undeclared))
        score -= penalty
        findings.append(
            {
                "severity": "yellow",
                "message": f"{len(undeclared)} relationship(s) with no declared cardinality — an agent's "
                "query planner can't be protected from fan-out on these.",
                "location": "relationships",
            }
        )

    look_alikes = _look_alike_pairs(model)
    if look_alikes:
        penalty = min(30, 10 * len(look_alikes))
        score -= penalty
        for a, b in look_alikes[:5]:
            findings.append(
                {
                    "severity": "red",
                    "message": f"Look-alike measures '{a}' and '{b}' have no contrasting description — "
                    "an agent will guess between them (Part 7, symptom-triage: 'the agent picks the "
                    "wrong measure').",
                    "location": f"{a} / {b}",
                }
            )

    facts_without_grain = [o for o in model.objects if any(f.role == "Measure" for f in o.fields) and not o.grain_stated]
    if facts_without_grain:
        penalty = min(20, 5 * len(facts_without_grain))
        score -= penalty
        for obj in facts_without_grain[:5]:
            findings.append(
                {
                    "severity": "yellow",
                    "message": f"Object '{obj.name}' holds measures but its description doesn't state a "
                    "grain ('one row per ...') — mixed-grain risk (Part 3).",
                    "location": obj.name,
                }
            )

    score = max(0.0, score)
    if not findings:
        findings.append({"severity": "green", "message": "No structural red flags detected.", "location": "-"})
    return score, findings, look_alikes or cycle


def score_descriptions(model: NormModel) -> Tuple[float, List[dict]]:
    findings: List[dict] = []
    objs_with_desc_and_grain = sum(1 for o in model.objects if is_real_description(o.description, o.name) and o.grain_stated)
    obj_ratio = objs_with_desc_and_grain / len(model.objects) if model.objects else 0.0

    all_fields = model.all_fields()
    fields_with_desc = sum(1 for f in all_fields if is_real_description(f.description, f.label or f.name))
    field_ratio = fields_with_desc / len(all_fields) if all_fields else 0.0

    score = 100.0 * (0.5 * obj_ratio + 0.5 * field_ratio)

    if obj_ratio < 1.0:
        missing = len(model.objects) - objs_with_desc_and_grain
        findings.append(
            {
                "severity": _sev(obj_ratio * 100),
                "message": f"{missing}/{len(model.objects)} object(s) lack a description that states their grain.",
                "location": "objects",
            }
        )
    if field_ratio < 1.0:
        missing = len(all_fields) - fields_with_desc
        findings.append(
            {
                "severity": _sev(field_ratio * 100),
                "message": f"{missing}/{len(all_fields)} field(s) lack a real (non-trivial) description.",
                "location": "fields",
            }
        )
    if not findings:
        findings.append({"severity": "green", "message": "All objects and fields carry real descriptions.", "location": "-"})
    return score, findings


def score_synonyms(model: NormModel) -> Tuple[float, List[dict]]:
    all_fields = model.all_fields()
    business_fields = [f for f in all_fields if not f.name.lower().endswith("id")]
    with_syn = sum(1 for f in business_fields if f.synonyms)
    ratio = with_syn / len(business_fields) if business_fields else 0.0
    score = 100.0 * ratio

    findings: List[dict] = []
    if model.fmt == "tds":
        findings.append(
            {
                "severity": "red",
                "message": "Classic PDS format has no synonym concept — business vocabulary mapping "
                "(reps/AEs/sellers -> User) has to be added in Tableau Next or an agent will guess.",
                "location": "format",
            }
        )
    elif ratio < 1.0:
        findings.append(
            {
                "severity": _sev(score),
                "message": f"{len(business_fields) - with_syn}/{len(business_fields)} business-facing "
                "field(s) have no synonyms.",
                "location": "fields",
            }
        )
    else:
        findings.append({"severity": "green", "message": "Synonyms present on all business-facing fields.", "location": "-"})
    return score, findings


def score_metrics(model: NormModel) -> Tuple[float, List[dict]]:
    measure_fields = model.measure_fields()
    metrics = model.metrics
    findings: List[dict] = []

    if model.fmt == "tds":
        findings.append(
            {
                "severity": "red",
                "message": "Classic PDS format has no governed-metrics concept — ratios like win rate "
                "will be improvised ad hoc per dashboard (Part 5/6) unless migrated to Tableau Next.",
                "location": "format",
            }
        )
        return 0.0, findings

    ratio_like = [f for f in model.calculated_fields if f.aggregation == "UserAgg"]
    ungoverned_ratios = [f for f in ratio_like if not any(m.get("measurementReference", {}).get("calculatedFieldApiName") == f.name for m in metrics)]

    coverage = len(metrics) / max(1, len(measure_fields))
    score = 100.0 * min(1.0, coverage)

    if ungoverned_ratios:
        penalty = min(40, 10 * len(ungoverned_ratios))
        score = max(0.0, score - penalty)
        for f in ungoverned_ratios[:5]:
            findings.append(
                {
                    "severity": "red",
                    "message": f"Ratio calc field '{f.label or f.name}' (UserAgg) has no semantic metric "
                    "wrapping it — an agent will improvise a fresh definition (Part 5/6).",
                    "location": f.name,
                }
            )

    if not metrics:
        findings.append(
            {
                "severity": "red",
                "message": "No semantic metrics defined at all — every 'what's our X' question gets "
                "answered by improvised SUM/AVG rather than a lookup.",
                "location": "metrics",
            }
        )
    elif coverage < 1.0 and not ungoverned_ratios:
        findings.append(
            {
                "severity": "yellow",
                "message": f"{len(metrics)} metric(s) defined against {len(measure_fields)} measure field(s) "
                "— some measures still have no governed lookup.",
                "location": "metrics",
            }
        )

    if not findings:
        findings.append({"severity": "green", "message": "Governed metrics cover the model's measures.", "location": "-"})
    return score, findings


def score_defaults(model: NormModel) -> Tuple[float, List[dict]]:
    keys = ("currency", "fiscal_year_start", "default_date_field")
    present = [k for k in keys if model.defaults.get(k)]
    score = 100.0 * len(present) / len(keys)

    findings: List[dict] = []
    missing = [k for k in keys if k not in present]
    if missing:
        findings.append(
            {
                "severity": _sev(score),
                "message": f"No stated default for: {', '.join(missing)} — an agent asked 'this year' "
                "or 'the amount' will guess and be silently wrong for half the org (Part 7's YTD trap).",
                "location": "business preferences",
            }
        )
    else:
        findings.append({"severity": "green", "message": "Currency, fiscal year, and default date field are all stated.", "location": "-"})
    return score, findings


def score_degrade(model: NormModel) -> Tuple[float, List[dict]]:
    text_blob = " ".join(
        (o.description or "") for o in model.objects
    ) + " ".join((f.description or "") for f in model.all_fields())
    text_blob = text_blob.lower()

    hits = [kw for kw in DEGRADE_KEYWORDS if kw in text_blob]
    score = 100.0 if hits else 0.0

    findings = [
        {
            "severity": "green" if hits else "yellow",
            "message": (
                f"Found degrade-honestly language ({', '.join(hits)}) in descriptions."
                if hits
                else "No detectable 'absence vs. zero' or Unknown-member language in descriptions — "
                "best-effort heuristic, may under-count (Part 7 Tier 5)."
            ),
            "location": "descriptions",
        }
    ]
    return score, findings


def score_model(model: NormModel) -> dict:
    structural_score, structural_findings, cap_triggers = score_structural(model)
    descriptions_score, descriptions_findings = score_descriptions(model)
    synonyms_score, synonyms_findings = score_synonyms(model)
    metrics_score, metrics_findings = score_metrics(model)
    defaults_score, defaults_findings = score_defaults(model)
    degrade_score, degrade_findings = score_degrade(model)

    dims = {
        "structural": structural_score,
        "descriptions": descriptions_score,
        "synonyms": synonyms_score,
        "metrics": metrics_score,
        "defaults": defaults_score,
        "degrade": degrade_score,
    }
    overall = sum(dims[k] * WEIGHTS[k] for k in WEIGHTS)

    level_code, level_label = _band(overall)
    capped_reason = None
    if cap_triggers and level_code not in ("L1",):
        rank = [code for _, code, _ in LEVEL_BANDS]
        if rank.index(level_code) < rank.index("L2"):
            level_code, level_label = "L2", "Basic"
            capped_reason = "Circular reference or unresolved look-alike measure pair caps level at L2."

    return {
        "name": model.name,
        "format": model.fmt,
        "overall": round(overall, 1),
        "level_code": level_code,
        "level_label": level_label,
        "capped_reason": capped_reason,
        "dimensions": {
            "structural": {"score": round(structural_score, 1), "findings": structural_findings},
            "descriptions": {"score": round(descriptions_score, 1), "findings": descriptions_findings},
            "synonyms": {"score": round(synonyms_score, 1), "findings": synonyms_findings},
            "metrics": {"score": round(metrics_score, 1), "findings": metrics_findings},
            "defaults": {"score": round(defaults_score, 1), "findings": defaults_findings},
            "degrade": {"score": round(degrade_score, 1), "findings": degrade_findings},
        },
        "parse_warnings": model.parse_warnings,
    }
