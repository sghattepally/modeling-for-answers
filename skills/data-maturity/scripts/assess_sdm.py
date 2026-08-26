#!/usr/bin/env python3
"""Assess a single semantic data model (SDM) for agent-readiness.

Accepts a Tableau Next SDM export (JSON), a hand-authored SDM spec (YAML with the
same key shape), or a classic Tableau published data source (.tds / .tdsx). Format
is auto-detected — see references/format-detection.md for the detection rules.

Usage:
    python scripts/assess_sdm.py path/to/model.json
    python scripts/assess_sdm.py path/to/model.tdsx --json
    python scripts/assess_sdm.py path/to/model.json --org myorg   # + live eval
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.parse_sdm_json import parse_sdm_json  # noqa: E402
from lib.parse_tds import is_tds_path, parse_tds  # noqa: E402
from lib.score import score_model  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a hard dep documented in SKILL.md
    yaml = None


def load_model(path: str):
    name = os.path.splitext(os.path.basename(path))[0]

    if is_tds_path(path):
        return parse_tds(path, name)

    with open(path, "r", encoding="utf-8") as fh:
        raw_text = fh.read()

    data = None
    fmt = "sdm-json"
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        if yaml is None:
            raise RuntimeError(
                f"{path} is not valid JSON and PyYAML is not installed to try YAML. "
                "Install with: pip install pyyaml"
            )
        data = yaml.safe_load(raw_text)
        fmt = "yaml"

    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to an object/dict — got {type(data).__name__}")

    return parse_sdm_json(data, name, fmt=fmt)


SEVERITY_ICON = {"red": "🔴", "yellow": "🟡", "green": "🟢"}

DIMENSION_LABELS = {
    "structural": "Structural soundness",
    "descriptions": "Descriptions",
    "synonyms": "Synonyms",
    "metrics": "Governed metrics",
    "defaults": "Stated defaults",
    "degrade": "Degrades honestly",
}


def render_markdown(result: dict) -> str:
    lines = []
    lines.append(f"# Agent-Readiness Scorecard — {result['name']}")
    lines.append("")
    lines.append(f"**Format:** {result['format']}  ")
    lines.append(f"**Overall:** {result['overall']}/100 — **{result['level_code']} ({result['level_label']})**")
    if result["capped_reason"]:
        lines.append(f"  \n⚠️ **Capped:** {result['capped_reason']}")
    lines.append("")

    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dimension | Score | Verdict |")
    lines.append("|---|---|---|")
    for key, label in DIMENSION_LABELS.items():
        dim = result["dimensions"][key]
        icon = SEVERITY_ICON["green"] if dim["score"] >= 75 else SEVERITY_ICON["yellow"] if dim["score"] >= 40 else SEVERITY_ICON["red"]
        lines.append(f"| {label} | {dim['score']}/100 | {icon} |")
    lines.append("")

    lines.append("## Findings (by dimension)")
    lines.append("")
    for key, label in DIMENSION_LABELS.items():
        dim = result["dimensions"][key]
        lines.append(f"### {label}")
        for f in dim["findings"]:
            icon = SEVERITY_ICON.get(f["severity"], "")
            lines.append(f"- {icon} {f['message']} (`{f['location']}`)")
        lines.append("")

    all_findings = []
    for key in DIMENSION_LABELS:
        for f in result["dimensions"][key]["findings"]:
            if f["severity"] in ("red", "yellow"):
                all_findings.append((key, f))
    if all_findings:
        lines.append("## Biggest wins (ranked)")
        lines.append("")
        ranked = sorted(all_findings, key=lambda kv: 0 if kv[1]["severity"] == "red" else 1)
        for i, (dim_key, f) in enumerate(ranked[:5], start=1):
            lines.append(f"{i}. **{DIMENSION_LABELS[dim_key]}** — {f['message']}")
        lines.append("")

    if result["parse_warnings"]:
        lines.append("## Parse notes")
        lines.append("")
        for w in result["parse_warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score an SDM/PDS for agent-readiness")
    parser.add_argument("path", help="Path to SDM JSON, YAML, .tds, or .tdsx")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--org", type=str, default=None, help="SF CLI org alias — enables live eval (see references/live-eval.md)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Write report to this path instead of stdout")
    args = parser.parse_args()

    model = load_model(args.path)
    result = score_model(model)

    if args.org:
        result["live_eval"] = {
            "status": "not_run",
            "reason": "Live eval requires the tableau-semantic-authoring auth pattern and a "
            "customer eval-config.yaml — see references/live-eval.md. This CLI accepts --org "
            "as a placeholder hook; wire it up per that doc before relying on it.",
        }

    output = json.dumps(result, indent=2) if args.json else render_markdown(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
