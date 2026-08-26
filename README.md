# Modeling for Answers
## Data Modeling Foundations for Tableau Next

*A seven-part series on getting the shape of your data right — so your dashboards are fast, your
numbers are correct, and your AI agent can be trusted.*

> **Version 2.0** · Last updated 25 August 2026
> Product specifics verified against Tableau Next, API v66.0.
> Every figure in the series is derived from [`data/`](data/) — run `python3 data/verify_numbers.py`.

Everything here is public and reproducible: **https://github.com/sghattepally/modeling-for-answers**

```bash
git clone https://github.com/sghattepally/modeling-for-answers.git
cd modeling-for-answers
python3 data/verify_numbers.py
```

---

## Why this series

If you've built a dashboard, a metric, or an AI agent on top of a semantic data model, you've
probably hit one of these: a number that's just *wrong* and you can't explain why, a dashboard
that crawls, or an agent that confidently answers the wrong question.

The instinct is to blame the tool. Nine times out of ten, it isn't the tool — it's the **shape
of the data underneath**: how your tables are defined and how they relate. Get the shape right
and everything above it gets faster, cheaper, and correct. Get it wrong and no amount of tuning,
prompting, or compute will save you.

This series teaches the fundamentals of dimensional data modeling — generically, so they apply
whether you work in Tableau Next, a tabular model in Power BI, or a warehouse in Snowflake — and
proves each concept inside a **Tableau Next semantic data model (SDM)** so you can see it
working. Every part ends on a real failure and how to fix it.

## Who it's for

- Analysts and admins assembling semantic models who were never formally taught to model.
- Data Cloud and CRM practitioners fluent in ETL and data products, newer to dimensional modeling.
- Tableau users who historically relied on upstream teams to shape the data for them.
- Data architects who know modeling but are new to Salesforce object realities (record types,
  person vs. business accounts, circular references).

No prior data-modeling background is assumed. Concepts are introduced in plain language first,
then made concrete.

## How it's built

The whole series follows **one running example** so it compounds: we start with a single fact —
**Opportunities** (your pipeline) — and its dimensions (Account, User, Product, Date). Midway we
add a second fact — **Orders** (your actuals) — and by the end we've layered on governed metrics
and the semantic metadata an AI agent needs. Each part builds directly on the last.

### Nothing here is asserted

Every number in the series comes from a deliberately tiny dataset — 11 opportunities, 9 orders —
that you can read in a minute and check by hand. It lives in [`data/`](data/), and
[`data/verify_numbers.py`](data/verify_numbers.py) asserts every figure the articles quote — the
narrative, the reference material and the eval set alike. If a claim in an article and the script
ever disagree, the script is right and the article is a bug.

The dataset is tuned so each teaching moment lands on a clean, memorable number: a $100,000 deal
that reads as $300,000, a chasm trap that inflates bookings 2.08×, one field name with four
defensible win rates, and a $120,000 gap between two readings of "this year."

---

## The seven parts

**[Part 1 — Facts, Dimensions & the Shape of Your Data](session-1-facts-and-dimensions.md)**
The two building blocks everything rests on, why modeling isn't ETL, and why a single wide
"let the agent figure it out" table gives you wrong, slow answers. Sidebars on slowly changing
dimensions and why Date deserves to be a real table.

**[Part 2 — Relationships vs. Joins](session-2-relationships-vs-joins.md)**
Why a semantic relationship is not a join, why queries are *economical* (they won't travel
across a relationship unless a field forces them to), and why that's the reason your filter
sometimes does nothing at all. Which direction filters actually flow, role-playing dimensions,
and what happens to a fact row whose dimension key doesn't match.

**[Part 3 — Grain, Fan-out & the Chasm Trap](session-3-grain-fan-out-and-the-chasm-trap.md)**
A second fact joins the model and revenue starts multiplying. Grain as the question you must
answer first, fan-out turning $100,000 into $300,000, and the chasm trap that inflates two facts
by *different* factors while silently deleting the rows you most want to see.

**[Part 4 — Conformed Dimensions, Junctions & the Whitespace Payoff](session-4-conformed-dimensions-junctions-whitespace.md)**
The fix. Conformed dimensions, drill-across, and the full outer join that everyone leaves out.
Junction objects for honest many-to-many, the allocation factor that stops "revenue by product"
exceeding total revenue, and the whitespace and cross-sell view you cannot build from a flat
table.

**[Part 5 — Calculated Fields That Scale](session-5-calculated-fields-that-scale.md)**
Row-level vs. aggregate calculations, the two different ways a ratio goes wrong (`SUM(a/b)` is
nonsense; `AVG(a/b)` is *plausible* nonsense, which is worse), measures you're not allowed to
sum at all, and how one innocent formula drags an entire dashboard down.

**[Part 6 — Order of Operations & Context in the Viz Layer](session-6-order-of-operations-and-context.md)**
Why the same field shows two different — and both correct — numbers on two dashboards. The exact
order of operations, why `FIXED` ignores a dimension filter but respects a context filter, and
one field name producing four defensible answers with an 18-point spread.

**[Part 7 — Modeling for the Agent](session-7-modeling-for-the-agent.md)**
How an AI agent inherits and *amplifies* every modeling decision you've made, the semantic
metadata that makes it trustworthy, the line between helpful standardization and brittle
overfitting, and how to actually *evaluate* whether it's getting the right answers.

---

## Reference material

These stand outside the narrative and are meant to be used, not read front to back.

| | |
|---|---|
| [**Glossary**](reference/glossary.md) | Every term the series introduces, defined without circularity. |
| [**Symptom triage**](reference/symptom-triage.md) | Start from what you observed — "my total is 3× too big" — and work back to the cause. |
| [**Exercises**](reference/exercises.md) | Per-part practice with worked answers, grounded in the sample dataset. |
| [**Going deeper**](reference/going-deeper.md) | Appendices on the topics the narrative keeps brief: SCD types, date dimensions, referential integrity, additivity, and where the trap terminology disagrees across vendors. |

## The artifacts

| | |
|---|---|
| [`data/`](data/) | The dataset, its builder, and the script that verifies every figure. |
| [`diagrams/`](diagrams/) | All 18 diagrams and the generator that produces them, with text-fit assertions so labels cannot overflow. |
| [`Semantic Models/`](Semantic%20Models/) | The model specification, the governed metrics in the form the API takes, and the agent eval set. |

---

## The one idea underneath all seven

**Your model's shape decides whether your answers are fast and correct.** Relationships, grain,
calculations, context, and agent metadata are all just ways of getting that shape right — and
keeping it right as your data, your dashboards, and your questions grow.

Or, as Part 1 puts it: **model like an architect, build like a builder.** A flawless build on a
bad blueprint still falls down.

*Read the parts in order the first time through; each one assumes the last. After that, they
stand alone as references.*
