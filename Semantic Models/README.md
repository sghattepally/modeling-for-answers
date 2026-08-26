# Semantic Models

*The model the series builds, as artifacts rather than prose.*

Back to [series overview](../README.md)

---

Part 1 promises that each concept gets proved "inside a Tableau Next semantic data model." This
folder is where that promise is kept.

| File | What it's for | Read it when |
|---|---|---|
| [`agent-eval-set.md`](agent-eval-set.md) | Twenty questions with known answers, tiered by what they test. | You want to know whether it works. |

## Coming shortly

The model specification and the calculated-field and metric definitions are being rebuilt as a
genuine Tableau Next export rather than a hand-written approximation, and will be published here
once that export exists.

That is a deliberate choice. A hand-written specification of a product's metadata is a drawing of
the thing rather than the thing, and it goes stale in ways a reader cannot detect — the same
objection this folder already makes to faking product screenshots. The eval set does not have that
problem: its expected values come from [`../data/`](../data/), so it stands on its own.

Until then, the model is described in prose across the series, and every figure the eval set
asserts is checkable today:

```bash
python3 data/verify_numbers.py
```

## What's deliberately not here

**Real product screenshots.** Several places in the series call for a screenshot of an actual
Tableau Next panel — the calculated-field editor, the governed metric definition, the semantic
metadata panel. Those are marked in the articles as `> **Screenshot needed**` and left for you to
capture from your own org. A drawn approximation of a product UI would be worse than nothing: it
would look authoritative and be wrong the moment the UI changes.

Everything conceptual is drawn instead, in [`../diagrams/`](../diagrams/), and clearly a diagram
rather than a fake interface.
