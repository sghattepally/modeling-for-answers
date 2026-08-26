# Live Eval — the dynamic layer

The static rubric (`maturity-rubric.md`) scores an SDM from its metadata alone, offline, at scale.
Live eval is the optional next step: actually asking a live agent the eval-set questions and
checking whether it gets them right. This doc explains the design and how to wire it up — the
`--org` flag on `assess_sdm.py` is currently a placeholder hook, not a finished integration; treat
this file as the spec for finishing it.

## Design principle: the skill is the dynamic thing, not the script

[`data/verify_numbers.py`](../../../data/verify_numbers.py) in this repo is a **teaching artifact**.
Its hardcoded `AS_OF`, `FISCAL_START_MONTH`, stage-name sets, and expected literals (`== 250000`)
are correct for its actual job — keeping the *Modeling for Answers* series honest against its own
tiny, hand-built dataset. Every one of those constants is a fact about *that* sample, not about a
customer's data. It ships here as the **worked reference** this skill imitates, never as something
you'd hand a customer to run.

The reason a single "dynamic script" can't fully replace the skill: the *compute* logic
(`SUM(amount) WHERE stage IN open_stages`) is generic and portable across customers, but the
*expected answer* can never be a baked-in literal — you don't know a customer's right answer in
advance. A parameterized script can only flex along axes you pre-wired (swap the date, swap the
stage vocab); it can't invent a check for a trap it's never seen in that customer's model. The
skill can, because it's reasoning over the parsed model: given *this* model's grain risks, it emits
a fan-out check on *this* model's fact tables; given *its* role-playing dimensions, it emits a
check on *its* date fields.

## Two ways to get ground truth (neither is a literal)

`verify_numbers.py` fuses "compute the number" and "assert it equals X" into one hardcoded step.
Live eval splits those:

1. **Compute the true answer from the customer's own data.**
   - *Config-backed*: the customer fills in a small `eval-config.yaml` — `as_of` date, fiscal year
     start month, currency, and a field-mapping section (which field is stage / amount / close
     date / owner). The skill reads their source CSVs/extract and derives the known-good number
     the same way `verify_numbers.py` does, just parameterized instead of hardcoded.
   - *Query-backed*: same compute logic, issued as SQL against their Data Cloud / warehouse instead
     of CSVs, so "the known answer" is a live query result rather than a static file.
2. **Ask the live agent the same question** (via the Tableau Next agent/chat surface) and compare
   its answer to the derived ground truth.

## Question set

Reuse [`Semantic Models/agent-eval-set.md`](../../../Semantic%20Models/agent-eval-set.md) as the
template — its 20 questions across 5 tiers (navigable → grain-respecting → own-definitions →
stated-conventions → degrades-honestly) are generic in *shape* even though the specific expected
values in that file are specific to the sample dataset. For a real customer, generate the
customer-specific version of each tier from their parsed model:

| Tier | Generic shape | How to generate for a customer's model |
|---|---|---|
| 1 — navigable | "What's my open pipeline?" | Substitute the customer's fact/stage-filter field names |
| 2 — grain | "Amount for a specific record with line items" | Pick a real header+line-item pair from their data |
| 3 — definitions | "What's our win rate?" | Only generatable if a ratio-like calc field exists in their model |
| 4 — conventions | "How are we doing this year?" | Only generatable if fiscal defaults are stated (else: this question exposes the gap, don't skip it) |
| 5 — degrades honestly | "How's [account with no data] doing?" | Pick a real dimension member absent from the fact |

## Scoring and output

Append a "Live Eval" section to the per-SDM scorecard: tier-by-tier pass counts, and for any failed
question, the question text, the agent's answer, the derived-truth answer, and which of the four
Part-7 root causes it maps to (model wrong / metric ungoverned / context not baked in / metadata
missing) — same triage order as `agent-eval-set.md`'s scoring sheet.

## Auth

Reuse the pattern already documented in `tableau-semantic-authoring`
(`~/.claude/skills/tableau-semantic-authoring/references/api-reference.md` and its
`scripts/lib/sf_api.py`):

```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

## Status

Not yet implemented — `assess_sdm.py --org <alias>` currently reports `"status": "not_run"` and
points here. This is intentionally scoped out of the first build (see the plan's "Out of scope"):
the static rubric is the part that has to work offline and at scale for every customer; live eval
is additive and needs an authenticated org plus a customer-specific eval-config, which most
first-pass engagements won't have yet.
