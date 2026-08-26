# Agent-Readiness Maturity Rubric

The scoring logic in `scripts/lib/score.py` implements this rubric exactly — if you change a
weight or threshold, change it in both places. This file exists so the numbers are inspectable
and tunable, not buried in code.

Six dimensions, each scored 0–100, combined into one overall 0–100 score. The dimensions mirror
the five-layer metadata stack from
[Part 7 — Modeling for the Agent](../../../session-7-modeling-for-the-agent.md)
(correct model → descriptions → synonyms → governed metrics → business preferences), plus a sixth
for "degrades honestly" pulled from the eval set's Tier 5.

## Dimensions and weights

| Dimension | Weight | What it measures | Where it comes from |
|---|---|---|---|
| Structural soundness | 25% | Circular relationship references, undeclared cardinality, look-alike measures with no contrasting description, facts with measures but no stated grain | [reference/symptom-triage.md](../../../reference/symptom-triage.md) |
| Descriptions | 25% | % of objects with a real description that states a grain sentence; % of fields with a real (non-trivial) description | Part 7, "Descriptions on objects and fields" |
| Synonyms | 15% | % of business-facing fields carrying synonyms | Part 7, "Synonyms and business vocabulary" |
| Governed metrics | 20% | Coverage of semantic metrics against measure fields; whether `UserAgg` ratio calc fields are wrapped by a metric | Part 7, "Governed metrics"; Part 5/6 |
| Stated defaults | 10% | Whether currency, fiscal-year start, and default date field are declared | Part 7, "Business preferences and defaults" |
| Degrades honestly | 5% | Heuristic scan for "no data"/"absence" language vs. silent zeros | Eval set Tier 5 |

"Structural soundness" is weighted equally with "Descriptions" because Part 7 is explicit that
metadata amplifies a model — it cannot repair one: a beautifully described model with a circular
reference or fan-out risk still produces wrong answers, just more persuasively.

## What counts as a "real" description

A description only counts if it's at least 10 characters **and** isn't just the field's own name
restated (e.g. a description of `Amount` that literally says "Amount"). This threshold exists
because exports frequently auto-populate a description with the label — that's noise, not
metadata, and would otherwise inflate the score for free. See `is_real_description()` in
`scripts/lib/normalize.py`.

## Level bands

| Score | Level | Label |
|---|---|---|
| ≥ 85 | L5 | Agent-ready |
| 70–84 | L4 | Governed |
| 50–69 | L3 | Emerging |
| 30–49 | L2 | Basic |
| < 30 | L1 | Ad-hoc |

## The L2 cap (gate)

Any circular relationship reference, **or** any unresolved look-alike-measure pair (similar labels,
neither with a real contrasting description), caps the level at **L2 regardless of the weighted
score**. This borrows the "circular reference is always CRITICAL" rule from
`tn-perf-static-review/references/sdm-complexity.md` — a structural defect this severe means the
model is actively dangerous to point an agent at, no matter how well everything else is described.

## Format-specific behavior

Classic `.tds`/`.tdsx` published data sources have no synonym concept, no semantic-metrics API,
and no business-preferences block. Those dimensions score at or near zero **by design**, not as a
parser failure — this is the correct signal that a classic PDS-as-SDM needs migration/enrichment
before it can be agent-ready. `parse_tds.py` documents this via `parse_warnings` on the model, and
`score.py`'s synonyms/metrics findings call it out explicitly rather than silently zeroing.

## Known heuristic limits

- **Look-alike detection** uses a string-similarity threshold (`difflib.SequenceMatcher` ratio ≥
  0.55) on field labels — it will miss semantically similar but differently-named fields (e.g.
  `ACV` vs. `Annual_Value`) and may occasionally flag unrelated fields with coincidentally similar
  names. Treat findings as leads to check, not certainties.
- **Grain-stated detection** looks for the literal phrases "one row per", "one row =", or "grain:"
  in an object's description. A grain sentence phrased differently won't be detected — this is a
  precision/recall tradeoff in favor of not fabricating credit for absent structure.
- **Degrade-honestly** is a keyword scan over description text, not a live behavioral test. A
  model can score 0 here and still degrade honestly in practice — this dimension is weighted
  lightest (5%) for exactly that reason. The live-eval mode (`references/live-eval.md`) is the
  real test.
