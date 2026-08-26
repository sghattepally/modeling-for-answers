# Semantic Models

*The model the series builds, as artifacts rather than prose.*

Back to [series overview](../README.md)

---

Part 1 promises that each concept gets proved "inside a Tableau Next semantic data model." This
folder is where that promise is kept. Three files, each for a different job.

| File | What it's for | Read it when |
|---|---|---|
| [`sales-pipeline-model.yaml`](sales-pipeline-model.yaml) | The blueprint — objects, grains, cardinality, conformance, SCD types, business preferences, and the multi-fact query policy. | You want to review or agree the model design with people. |
| [`calculated-fields-and-metrics.md`](calculated-fields-and-metrics.md) | The governed metrics, in the form the Tableau Next API actually takes, with the `UserAgg` rule and expected values. | You want to build it in an org. |
| [`agent-eval-set.md`](agent-eval-set.md) | Twenty questions with known answers, tiered by what they test. | You want to know whether it works. |

## A note on the YAML

`sales-pipeline-model.yaml` is a **readable specification, not a product export.** Tableau Next
does not consume this file; it exists so a human can review the whole model — every grain, every
cardinality declaration, every default — on a few screens instead of clicking through a canvas.

That distinction matters because the two documents serve different readers. The YAML is the
architect's drawing. `calculated-fields-and-metrics.md` contains the actual API payloads and CLI
invocations, and that's the builder's instruction sheet. Part 1's whole argument is that these
are different jobs.

## The order to work in

1. **Read the YAML.** Particularly `multi_fact_policy` — the full outer join requirement is the
   thing most implementations get wrong, and it's the difference between having whitespace
   analysis and not.
2. **Run `discover_sdm.py`** against your org to get the real object and field API names. Do not
   skip this; the placeholder names in the metrics file are almost certainly not yours.
3. **Create the calculated fields, then the metrics.** Metrics reference calculated fields by API
   name, so the field must exist first.
4. **Check each field against its expected value.** They're tabulated at the end of
   `calculated-fields-and-metrics.md` and asserted by
   [`../data/verify_numbers.py`](../data/verify_numbers.py).
5. **Run the eval set.** Tiers 1–4 should be 100%. Anything less points at a specific part of the
   series rather than at the agent.

## What's deliberately not here

**Real product screenshots.** Several places in the series call for a screenshot of an actual
Tableau Next panel — the calculated-field editor, the governed metric definition, the semantic
metadata panel. Those are marked in the articles as `> **Screenshot needed**` and left for you to
capture from your own org. A drawn approximation of a product UI would be worse than nothing: it
would look authoritative and be wrong the moment the UI changes.

Everything conceptual is drawn instead, in [`../diagrams/`](../diagrams/), and clearly a diagram
rather than a fake interface.
