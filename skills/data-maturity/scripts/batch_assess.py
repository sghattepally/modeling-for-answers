#!/usr/bin/env python3
"""Assess every SDM/PDS in a folder and produce a ranked roll-up.

Walks the folder for *.json, *.yaml, *.yml, *.tds, *.tdsx, scores each one with
the same logic as assess_sdm.py, writes one <name>.scorecard.md per file plus a
single maturity-rollup.csv sorted worst-first so the lowest-scoring models sort to
the top for triage.

Usage:
    python scripts/batch_assess.py path/to/folder
    python scripts/batch_assess.py path/to/folder --output-dir reports/
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from assess_sdm import load_model, render_markdown  # noqa: E402
from lib.score import score_model  # noqa: E402

SCANNABLE_EXTS = (".json", ".yaml", ".yml", ".tds", ".tdsx")

ROLLUP_FIELDS = [
    "name",
    "format",
    "overall",
    "level_code",
    "structural",
    "descriptions",
    "synonyms",
    "metrics",
    "defaults",
    "degrade",
    "capped_reason",
]


def find_candidates(folder: str):
    for root, _dirs, files in os.walk(folder):
        for fname in files:
            if fname.lower().endswith(SCANNABLE_EXTS):
                yield os.path.join(root, fname)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-score every SDM/PDS in a folder")
    parser.add_argument("folder", help="Folder to scan (recursive)")
    parser.add_argument("--output-dir", type=str, default=None, help="Where to write scorecards + rollup CSV (default: the input folder)")
    args = parser.parse_args()

    out_dir = args.output_dir or args.folder
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    skipped = []

    for path in sorted(find_candidates(args.folder)):
        try:
            model = load_model(path)
            result = score_model(model)
        except Exception as exc:  # noqa: BLE001 - report and continue the batch
            skipped.append((path, str(exc)))
            continue

        scorecard_name = os.path.splitext(os.path.basename(path))[0] + ".scorecard.md"
        scorecard_path = os.path.join(out_dir, scorecard_name)
        with open(scorecard_path, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(result))

        rows.append(
            {
                "name": result["name"],
                "format": result["format"],
                "overall": result["overall"],
                "level_code": result["level_code"],
                "structural": result["dimensions"]["structural"]["score"],
                "descriptions": result["dimensions"]["descriptions"]["score"],
                "synonyms": result["dimensions"]["synonyms"]["score"],
                "metrics": result["dimensions"]["metrics"]["score"],
                "defaults": result["dimensions"]["defaults"]["score"],
                "degrade": result["dimensions"]["degrade"]["score"],
                "capped_reason": result["capped_reason"] or "",
            }
        )

    rows.sort(key=lambda r: r["overall"])

    rollup_path = os.path.join(out_dir, "maturity-rollup.csv")
    with open(rollup_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ROLLUP_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scored {len(rows)} model(s). Roll-up: {rollup_path}")
    if skipped:
        print(f"Skipped {len(skipped)} file(s) that failed to parse:")
        for path, err in skipped:
            print(f"  - {path}: {err}")


if __name__ == "__main__":
    main()
