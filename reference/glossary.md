# Glossary

*Every term the series introduces, defined in plain language, with the Part that covers it and a
worked example from the dataset in `data/`.*

Back to [the series overview](../README.md).

Definitions here are deliberately short. Where a term needs a full treatment it points at the Part
that gives it one, or at [Going Deeper](going-deeper.md) for the appendix version. Every figure
quoted is asserted by `data/verify_numbers.py`.

---

## A

### Additive measure

A measure you can safely sum across every dimension in the model — time, account, product, owner.
Adding it up never changes what it means.

*[Part 5](../session-5-calculated-fields-that-scale.md). `[Order].[Amount]` is additive: the nine
orders sum to $600,000 whether you group by account, by month, or not at all.*

### Aggregate calculation

A calculation evaluated **after** rows are rolled up, so its inputs are already-summarized values.
Its cost scales with the number of groups in the view, not the number of rows in the table.

*[Part 5](../session-5-calculated-fields-that-scale.md). `SUM([Opportunity].[Amount])` for won deals
divided by the same for all closed deals is one division per group, not one per opportunity.*

### Aggregate filter

A filter that runs after aggregation and therefore removes summarized rows rather than source rows —
`SUM(Amount) > 100000`. You cannot know whether a group qualifies until you have summed it.

*[Part 6](../session-6-order-of-operations-and-context.md).*

### Allocation factor

The fraction of a parent measure that a bridge row is entitled to. Stored on the bridge so that
attribution is explicit and auditable rather than assumed.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). Opportunity `O-001` is
$100,000 across three line items of $40,000, $35,000 and $25,000, giving factors of 0.40, 0.35 and
0.25 — which sum to exactly 1.00.*

### Attribution

The decision about **how credit for a measure is divided** when one fact relates to many members of
a dimension. Equal split, split by line value, or full credit to every member — each answers a
different question, and only some of them add up.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). Giving every product on
`O-001` the full header amount reports $300,000 of product revenue for a $100,000 deal.*

---

## B

### Bridge object

A table whose rows exist purely to record pairings between two other tables, so that a genuine
many-to-many can be expressed without duplicating either side. Synonymous with **junction object**
and **associative object**; also called a bridge table in the warehouse literature.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). `Opportunity Line Item`
bridges `Opportunity` and `Product` — and carries its own `line_amount`, which is what makes correct
allocation possible.*

### Business preference

A standing instruction that resolves ambiguity a natural-language question leaves open: default
currency, default date field, whether "this year" means fiscal or calendar, which of two valid
definitions is the house default.

*[Part 7](../session-7-modeling-for-the-agent.md).*

---

## C

### Calculated field

An expression defined in the semantic model and evaluated at query time. In Tableau Next, calculated
field names end `_clc`. Calculated fields are model-level, so they reference other calculated fields
unqualified — `[Win_Rate_clc]` — while table fields are always qualified as
`[TableName].[FieldName]`. No double underscores anywhere.

*[Part 5](../session-5-calculated-fields-that-scale.md).*

### Cardinality

How many rows on one side of a relationship correspond to a row on the other side: many-to-one,
one-to-many, or many-to-many. It is the single most consequential thing you declare, because it tells
the engine whether an aggregation across that relationship needs protecting from duplication.

*[Part 2](../session-2-relationships-vs-joins.md). Many opportunities to one account is safe; one
opportunity to many line items multiplies the opportunity side.*

### Chasm trap

Two facts hanging off the same shared dimension, queried together through it. Because the facts share
a dimension but not a grain, the engine pairs every row of one fact with every row of the other for
each dimension member, inflating both totals.

*[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md). Joining `Orders` to `Opportunities`
through `Account` turns $600,000 of bookings into $1,245,000 — 2.08 times too big — and $1,250,000 of
opportunity value into $2,150,000.*

### Conformed dimension

A dimension defined once and used identically by more than one fact — same keys, same members, same
meaning. Conformance is what makes it legitimate to place two facts side by side.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). `Account` is conformed when
"Acme Corp, West, Enterprise" means precisely the same entity to `Opportunity` and to `Order`.*

### Context

The set of constraints the rest of a query treats as its fixed frame of reference. Promoting a filter
to context makes it apply first, so everything computed afterwards — percentages, ranks, ratios —
operates inside the world that filter defines.

*[Part 6](../session-6-order-of-operations-and-context.md). Put a region filter in context and
"percent of total" means percent of the West; leave it as an ordinary filter applied later and the
denominator may still be the whole company.*

### Cross-sell

Selling a product to an account that already buys something else from you. In a model, a cross-sell
target is a set difference: products bought by comparable accounts that this account has not bought.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md).*

---

## D

### Date dimension

A materialized table with one row per calendar date, carrying every attribute you might group or
filter by — calendar year, month, fiscal year, fiscal quarter, period flags. Building it once turns
"what does this year mean" from a guess into a modeling decision.

*[Part 1](../session-1-facts-and-dimensions.md) introduces it, [Part 7](../session-7-modeling-for-the-agent.md)
shows what happens without it. `data/calendar.csv` carries both `is_calendar_ytd` and `is_fiscal_ytd`,
and the whole point is that they disagree. See [Going Deeper](going-deeper.md#the-date-dimension).*

### Degenerate dimension

A dimension attribute that lives on the fact row itself because it has no attributes of its own and
no dimension table to belong to — an order number, an invoice number, an opportunity id. You group and
drill by it; you never join to it.

*Not covered in the narrative — see [Going Deeper](going-deeper.md#degenerate-and-junk-dimensions).
`order_id` viewed at order-line grain is degenerate: it identifies the order and describes nothing
else.*

### Dimension

The descriptive context you slice facts by — the "by what" of a question. Account, owner, product,
date. Dimensions are what you group and filter on; they carry no measures of their own.

*[Part 1](../session-1-facts-and-dimensions.md). `Account`, `User`, `Product` and the calendar are the
four dimensions of the series' spine model.*

### Dimension filter

A filter that narrows which source rows are considered at all, before any aggregation happens. It
changes the pool, and therefore changes every denominator downstream.

*[Part 6](../session-6-order-of-operations-and-context.md). Applying `Stage = Closed` as a dimension
filter is what turns win rate from 32.0% into 40.0% — it removed the three open opportunities from the
denominator.*

### Drill-across

The correct way to report two facts together: aggregate each fact **separately, at its own grain**,
then align the two summaries on their conformed dimension keys. Because you aggregate before aligning,
there is nothing left to duplicate.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). Bookings summed among orders
only ($600,000) and open pipeline summed among opportunities only ($250,000), then joined on account —
both totals match their sources.*

---

## E

### Economical query

The behavior of a query planner that refuses to traverse a relationship unless a field in the
question requires it. This is what keeps a large model cheap to query — and it is also why a filter
on an object the query never visited does nothing at all.

*[Part 2](../session-2-relationships-vs-joins.md).*

---

## F

### Fact

A measurable event: it has a date, one or more numeric measures, and keys pointing at the dimensions
that describe it. Facts are what you count, sum and average.

*[Part 1](../session-1-facts-and-dimensions.md). `Opportunity` (11 rows) and `Order` (9 rows) are the
two facts in the series model.*

### Fan-out

The multiplication that happens when you traverse a one-to-many relationship and aggregate a measure
from the "one" side. The join does not add value; it copies the parent value onto every child row, and
then you sum the copies.

*[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md). `O-001` is $100,000 with three line
items, so a naive `SUM([Opportunity].[Amount])` across those lines reads $300,000.*

### Fan trap

Fan-out along a single path with two consecutive one-to-many hops — `Account` → `Opportunity` →
`Opportunity Line Item`. A measure taken from the top of the chain fans out by everything below it.

*[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md). Note that the label is used
inconsistently across vendors and textbooks; see
[Going Deeper](going-deeper.md#a-note-on-terminology-fan-trap-and-chasm-trap).*

### Fiscal year

An accounting year that need not start in January. Which one you use is a modeling decision, not a
fact of nature, and it must be recorded in the date dimension rather than assumed.

*[Part 7](../session-7-modeling-for-the-agent.md). The dataset's fiscal year starts on 1 February,
which is why calendar year-to-date bookings read $600,000 and fiscal year-to-date bookings read
$480,000.*

---

## G

### Governed metric

A metric defined once in the semantic model, with its grain, filters and context settled and
published, so that every dashboard and the agent return the same number for the same word. In Tableau
Next, semantic metric names end `_mtc`.

*[Part 5](../session-5-calculated-fields-that-scale.md) defines them,
[Part 6](../session-6-order-of-operations-and-context.md) explains why they end arguments, and
[Part 7](../session-7-modeling-for-the-agent.md) makes them the agent's vocabulary of answers.*

### Grain

What one row of a table means. Not what the table contains — what a single row **represents**.
"One row per opportunity." "One row per product per order." Stating it out loud is the most
clarifying sentence in data modeling.

*[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md). The four grains in the dataset: 11
opportunities, 16 product-on-opportunity rows, 9 orders, 11 product-on-order rows.*

---

## J

### Join

A physical instruction to combine two tables on a key and return merged rows, executed whether or not
you use a column from the second table. A join is eager, and the moment the relationship is one-to-many
it changes the grain of the result.

*[Part 2](../session-2-relationships-vs-joins.md). See also **relationship**, which is the contrast
the whole Part is built on.*

### Junction object

See **bridge object**. In Salesforce you usually already have one: `Opportunity Line Item` between
Opportunity and Product, `Campaign Member` between Campaign and Contact.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md).*

### Junk dimension

A single small dimension assembled from several low-cardinality flags and indicators, holding one row
per combination that actually occurs. It keeps a swarm of yes/no columns off the fact table.

*Not covered in the narrative — see
[Going Deeper](going-deeper.md#degenerate-and-junk-dimensions) for the full treatment.*

---

## L

### Late-arriving dimension

A fact that lands before the dimension row it points at exists. Handle it deliberately — hold the
fact, or admit it against a placeholder member you can later resolve — because the default is silent
loss.

*[Part 2](../session-2-relationships-vs-joins.md). See
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling).*

### Level of detail (LOD)

The grain at which a measure is computed, which is not necessarily the grain being displayed. An LOD
expression lets you pin a measure to a stated grain regardless of the view:
`{ FIXED [Account].[Account Name] : SUM([Order].[Amount]) }` computes account bookings even in a view
laid out at order-line grain.

*[Part 6](../session-6-order-of-operations-and-context.md).*

---

## M

### Many-to-many

A relationship where rows on both sides can match many rows on the other. It cannot be drawn correctly
as a direct line; it needs a bridge object between the two.

*[Part 2](../session-2-relationships-vs-joins.md) names it,
[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md) fixes it. One opportunity involves
many products; one product appears on many opportunities.*

### Measure

A numeric column on a fact that you aggregate. Whether a given aggregation is *legitimate* depends on
the measure's additivity, not on whether the engine will let you do it.

*[Part 1](../session-1-facts-and-dimensions.md) and
[Part 5](../session-5-calculated-fields-that-scale.md).*

---

## N

### Non-additive measure

A measure that must never be summed or averaged across anything, because the arithmetic of the
aggregate is not the arithmetic of the parts. Ratios, rates, percentages and margins are all
non-additive: you recompute them from their numerator and denominator at the level you want.

*[Part 5](../session-5-calculated-fields-that-scale.md). Win rate is non-additive — the four
owner-level win rates in the dataset cannot be added, and averaging them is not the company rate
either.*

---

## O

### One big table

The anti-pattern of flattening every fact and every dimension into a single wide table so that the
tool, or the agent, can "figure it out". It duplicates measures wherever a one-to-many exists and
strips out the structural cues that tell a consumer which column means what.

*[Part 1](../session-1-facts-and-dimensions.md). Flatten the 11 opportunities against their 16 line
items and you have 16 rows with the header amount repeated — the protection against fan-out is gone,
because the copies are now indistinguishable from the original.*

### One-to-many

Cardinality where one row on the first side corresponds to many rows on the second. Traversing it
multiplies the "one" side, which is the mechanism behind fan-out.

*[Part 2](../session-2-relationships-vs-joins.md).*

### Order of operations

The fixed sequence in which the viz layer applies dimension filters, context, aggregation, aggregate
filters and table calculations. The same field yields different numbers depending on where in that
sequence its filter lands.

*[Part 6](../session-6-order-of-operations-and-context.md). Distinct from the order of operations
within a single calculation, which is [Part 5](../session-5-calculated-fields-that-scale.md).*

### Orphan row

A fact row whose foreign key has no matching row in the dimension. Under inner-join semantics it
disappears from every report that touches that dimension, and nothing on screen says a row went
missing.

*[Part 2](../session-2-relationships-vs-joins.md). See **Unknown member** for the fix, and
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling) for the full pattern.*

### Overfitting

Standardizing so aggressively that the model becomes brittle to legitimate variation — one hardcoded
fiscal calendar, one blessed phrasing, one permitted definition. Standardization removes ambiguity;
overfitting removes flexibility.

*[Part 7](../session-7-modeling-for-the-agent.md).*

---

## P

### Partial Cartesian product

The row explosion produced when two sets are paired on a key that is not unique in either — every row
of one matched against every row of the other, within each key value. It is the mechanism of the chasm
trap, and the reason the inflation factor is uneven across dimension members.

*[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md). Acme Corp has 3 orders and 3
opportunities, so joining them through `Account` returns 9 rows for that account alone; 18 rows across
the whole dataset.*

### Percent of total

A table calculation whose denominator is the total of whatever is in context. Change the context and
every percentage changes, without the formula changing at all.

*[Part 6](../session-6-order-of-operations-and-context.md).*

---

## R

### Referential integrity

The guarantee that every foreign key on a fact points at a row that exists in the dimension. Declared
integrity is a promise the engine may act on; enforced integrity is a constraint the data actually
satisfies. Confusing the two is how orphan rows go unnoticed.

*[Part 2](../session-2-relationships-vs-joins.md). See
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling).*

### Relationship

A declared possibility rather than an instruction: *these two objects are related, on this key, with
this cardinality — travel between them when a question requires it.* The engine crosses it only when a
field in the question forces the trip, and it aggregates each measure at its own grain rather than
merging rows up front.

*[Part 2](../session-2-relationships-vs-joins.md). A join welds two rooms into one; a relationship
puts a door between them.*

### Role-playing dimension

One conformed dimension related more than once to the same model, where each relationship means
something different. Each role is a separate path, and a question has to pick one.

*[Part 2](../session-2-relationships-vs-joins.md). The single calendar plays three roles here:
created date and close date on `Opportunity`, order date on `Order`. Two opportunities were created in
2025 and none closed in 2025 — "last year" is a different answer per role.*

### Row-level calculation

A calculation evaluated once per source row, before aggregation. Its cost scales with the row count,
which is why a row-level calculation on a high-cardinality leaf object is the expensive shape.

*[Part 5](../session-5-calculated-fields-that-scale.md). `quantity × unit price` on an order line is
row-level and stable, so it belongs upstream as a materialized column.*

---

## S

### Semantic data model (SDM)

The Tableau Next artefact that holds objects, their relationships and cardinality, calculated fields,
semantic metrics and the descriptive metadata an agent reads. It is where modeling decisions become
something the platform can act on.

*Every Part.*

### Semantic metric

A governed metric defined in the semantic data model. Names end `_mtc`. A metric carries its grain,
filters and context with it, which is what makes the same word return the same number everywhere.

*[Part 5](../session-5-calculated-fields-that-scale.md).*

### Semi-additive measure

A measure you can sum across some dimensions but not across time, because each period's value is a
snapshot of a stock rather than a flow. Headcount, inventory on hand, account balance, open pipeline
as at a date. Sum across accounts; take the period-end or period-average value across time.

*[Part 5](../session-5-calculated-fields-that-scale.md). Summing twelve monthly snapshots is the
classic way to report twelve times your real headcount. See
[Going Deeper](going-deeper.md#additivity).*

### Slowly changing dimension (SCD)

A dimension whose attributes change over time, and the set of techniques for deciding what happens to
history when they do.

- **Type 1 — overwrite.** The new value replaces the old. History is restated: every prior report
  now shows the current attribute. Right for corrections.
- **Type 2 — versioned.** A second row is added with effective-from and effective-to dates and a
  current flag, and each fact joins to the version in force at the time. History is preserved. Right
  when the change is itself something you report on.

*[Part 1](../session-1-facts-and-dimensions.md). If Acme Corp moves from West to East on 1 June 2026,
Type 1 reports all $200,000 of Acme bookings as East, while Type 2 keeps $150,000 in the West and
puts $50,000 in the East. Types 0, 3 and 4 are in
[Going Deeper](going-deeper.md#slowly-changing-dimensions).*

### Snowflake schema

A star whose dimensions are normalized further into sub-tables — Product to Product Family to
Department. More normalized, but every extra hop is work at query time.

*[Part 1](../session-1-facts-and-dimensions.md).*

### Star schema

One fact in the center with its dimensions arranged directly around it, each one hop away. Easy to
read, cheap to query, and unambiguous to both humans and agents. The default shape.

*[Part 1](../session-1-facts-and-dimensions.md).*

### Surrogate key

A meaningless, model-owned identifier for a dimension row, as distinct from the natural business key.
You need one as soon as a dimension is versioned, because Type 2 gives the same business entity
several rows and a fact has to point at one specific version.

*A mechanic of the Type 2 versioning introduced in
[Part 1](../session-1-facts-and-dimensions.md); the detail is in
[Going Deeper](going-deeper.md#slowly-changing-dimensions).*

### Synonym

An alternative word mapped onto a field or metric so that the agent is not defeated by vocabulary —
"reps", "AEs", "sellers" and "owners" all reaching `User`.

*[Part 7](../session-7-modeling-for-the-agent.md).*

---

## T

### Table calculation

A calculation that runs last, on the already-aggregated result set — running total, rank,
percent of total, difference from previous. It sees summarized rows, never source rows.

*[Part 6](../session-6-order-of-operations-and-context.md).*

---

## U

### Unknown member

An explicit, deliberately created dimension row — "Unknown Account" — that orphan facts are routed to
instead of being dropped. It converts an invisible loss of revenue into a visible number somebody will
question.

*[Part 2](../session-2-relationships-vs-joins.md). See
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling).*

### UserAgg

The Tableau Next aggregation type you set on a calculated field whose expression **already contains an
aggregation**. A ratio written as `SUM(...) / SUM(...)` is finished arithmetic; without `UserAgg` the
engine double-aggregates it and the result is wrong.

*[Part 5](../session-5-calculated-fields-that-scale.md). Every ratio metric in the series — win rate,
pipeline coverage — needs it.*

---

## W

### Whitespace

Demand your pipeline cannot see, expressed as a set difference between two conformed facts: accounts
that bought and have nothing open, products that sell and are never forecast. It is a capability the
model's shape either gives you or denies you.

*[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md). Four accounts bought before and
have nothing open — Delta Foods, Everest Health, Fjord Logistics and Granite Bank, $300,000 of past
bookings. Two products sell but are absent from the open pipeline — Gadget and Gizmo, $235,000 of
demand.*

---

## Y

### Year to date (YTD)

Everything from the start of the current year up to today — where "year" is whichever year the model
says it is. The ambiguity is the whole problem, and it is settled in the date dimension, not in the
question.

*[Part 7](../session-7-modeling-for-the-agent.md). As at 25 August 2026, calendar YTD bookings are
$600,000 and fiscal YTD bookings are $480,000 — a $120,000 gap, 20% of the number, caused by a single
January order, `R-006`, placed by Delta Foods on 20 January 2026.*
