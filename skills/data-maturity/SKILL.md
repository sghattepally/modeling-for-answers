---
name: data-maturity
description: |
  Score a Semantic Data Model (SDM) for agent-readiness — whether an AI agent pointed at it will
  give trustworthy answers. Reads any SDM a customer provides: a Tableau Next SDM export
  (JSON/YAML) or a classic published data source (.tds/.tdsx) — auto-detected. Works fully offline
  on supplied files; no org auth required. Produces a 0-100 score, an L1-L5 maturity level, and
  ranked findings tied back to specific objects/fields. Scans a single file or an entire folder at
  scale, emitting one scorecard per SDM plus a ranked roll-up CSV.

  Trigger: "is this SDM agent-ready", "is this PDS agent-ready", "check data maturity", "score my
  semantic model for agents", "how agent-ready is our data model", "assess this SDM/data source",
  "which of our models need work before we point an agent at them".
metadata:
  version: "1.0"
  tags: [tableau-next, sdm, pds, agent-readiness, data-maturity, semantic-model]
allowed-tools: Read Bash(python3:*) Write
---

# Data Maturity — Agent-Readiness Scoring for SDMs

Scores a Semantic Data Model for whether an AI agent can be trusted to answer questions against it
correctly. **Terminology note:** every published data source is itself a semantic data model, just
an older, thinner one — "SDM" is the umbrella term this skill uses; "classic PDS" (`.tds`/`.tdsx`)
and "Tableau Next SDM" (JSON/YAML) are the two concrete formats it parses.

The rubric operationalizes [Part 7 of *Modeling for Answers*](../../session-7-modeling-for-the-agent.md)
(descriptions → synonyms → governed metrics → business preferences, all resting on a correct
model) plus the structural failure catalog in
[reference/symptom-triage.md](../../reference/symptom-triage.md). Full detail:
[references/maturity-rubric.md](references/maturity-rubric.md).

## When to use this skill

- A customer hands you an SDM export, a `.tds`/`.tdsx`, or a folder of many, and asks "is this
  ready for an agent?"
- You need to triage a portfolio of PDSs to find which ones need enrichment work first.
- You want a repeatable, offline check before recommending a customer point Tableau Next Agent (or
  any agent) at a given model.

**Don't use this skill for:** creating or editing calc fields/metrics (use
`tableau-semantic-authoring`), dashboard performance (use `tableau-next-perf-expert`), or building
visualizations (use `tableau-next-author`). This skill is advisory-only — it never writes to the
customer's SDM.

## Procedure

1. **Identify what was supplied.** A single file, or a folder? What format(s)? Format is
   auto-detected per file — see [references/format-detection.md](references/format-detection.md).
   If nothing was supplied, ask for a file or folder path — do not guess or fabricate a model.
2. **Single file** → run:
   ```bash
   python3 scripts/assess_sdm.py path/to/model.json
   ```
   Add `--json` for machine-readable output, `-o report.md` to write instead of printing.
3. **Folder (batch/scale)** → run:
   ```bash
   python3 scripts/batch_assess.py path/to/folder --output-dir reports/
   ```
   Produces one `<name>.scorecard.md` per SDM found (recursively, any mix of `.json`/`.yaml`/
   `.tds`/`.tdsx`) plus one `maturity-rollup.csv` sorted worst-score-first for triage. Files that
   fail to parse are skipped and listed, not silently dropped.
4. **Read the result back to the user in plain language**, don't just dump the file: state the
   overall score and level, the single biggest-win fix, and whether an L2 cap was triggered
   (circular reference or unresolved look-alike measures — see the rubric doc for what that means
   and why it overrides the weighted score).
5. **If the user has a live, authenticated org** and wants to go further than static metadata
   analysis, mention the optional live-eval mode — see
   [references/live-eval.md](references/live-eval.md). It is not yet wired up end-to-end; treat it
   as a documented next step, not a working `--org` flag today.

## Output format

Each scorecard (see `scripts/assess_sdm.py:render_markdown`):

```
# Agent-Readiness Scorecard — <name>
**Format:** sdm-json
**Overall:** 62.0/100 — L3 (Emerging)

## Dimensions
| Dimension | Score | Verdict |
|---|---|---|
| Structural soundness | 80.0/100 | 🟢 |
| Descriptions | 45.0/100 | 🟡 |
| Synonyms | 0.0/100 | 🔴 |
...

## Findings (by dimension)
### Descriptions
- 🟡 12/20 field(s) lack a real (non-trivial) description. (`fields`)
...

## Biggest wins (ranked)
1. **Synonyms** — 18/20 business-facing field(s) have no synonyms.
...
```

The roll-up CSV columns: `name, format, overall, level_code, structural, descriptions, synonyms,
metrics, defaults, degrade, capped_reason` — one row per SDM, ascending by `overall` so the
weakest models are first.

## Rules

- **Never fabricate** a model or its metadata. If a file doesn't parse, report it as skipped with
  the parse error — don't guess at what it might have contained.
- **Advisory only.** Recommend fixes; never edit the customer's SDM, `.tds`, or export file.
- **Static-only unless told otherwise.** Don't assume org credentials exist or attempt live
  queries without the user explicitly providing an org alias and confirming live-eval is wanted.
- **Classic PDS scoring low on synonyms/metrics/defaults is expected, not a bug** — those concepts
  don't exist in that format. Say so plainly rather than treating it as a parser gap.

## Reference files

- [references/maturity-rubric.md](references/maturity-rubric.md) — the six dimensions, weights,
  level bands, and the L2 structural cap, with the reasoning behind each threshold.
- [references/format-detection.md](references/format-detection.md) — how JSON/YAML/`.tds`/`.tdsx`
  are told apart and mapped into the shared normalized model.
- [references/live-eval.md](references/live-eval.md) — the design for the optional live-org eval
  mode, and why it has to be dynamic (skill-generated per customer) rather than a frozen script.

## Prerequisites

- Python 3.8+.
- `pyyaml` for YAML input (`pip install pyyaml`) — JSON and `.tds`/`.tdsx` work with the standard
  library alone.
