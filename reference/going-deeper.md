# Going Deeper

*Appendices on the topics the main narrative keeps deliberately brief so it stays readable — slowly
changing dimensions, the date dimension, referential integrity, additivity, degenerate and junk
dimensions, and where the vocabulary disagrees with itself.*

Back to [the series overview](../README.md).

Each Part makes one point and moves on. That is the right choice for a narrative and the wrong choice
for a reference, so the material a Part mentions in a sentence gets a full treatment here. Nothing
below is optional knowledge — it is just knowledge that would have derailed the story.

---

## Slowly changing dimensions

Referenced from [Part 1](../session-1-facts-and-dimensions.md).

Dimension attributes change. An account moves region, a rep changes team, a product is reclassified, a
customer's segment is upgraded. Each change forces a question that is easy to skip and expensive to
skip: **what happens to the reports that were already produced?**

The techniques are conventionally numbered. The numbers matter less than the decision behind them,
which is always the same one: is this change a **correction** or an **event**?

### Type 0 — retain original

The attribute is set when the row is created and never updated. Original acquisition channel, date of
first purchase, original contract term, the credit score at the time of underwriting.

Type 0 is often best expressed as a *deliberate pair* of columns rather than as a policy: keep
`original_region` next to `current_region` and let the analyst pick. That is a Type 0 column living
inside a dimension managed by some other type — which is legitimate, and clearer than arguing about
which number the dimension "is".

**Use it when** the original value has permanent analytical meaning in its own right — cohort analysis
lives on Type 0 columns.

### Type 1 — overwrite

The new value replaces the old. One row per entity, no history, nothing to reconcile.

The consequence is not "you lose history"; that undersells it. **All prior reporting is restated.**
Every fact that ever pointed at that dimension row now groups under the current attribute value,
retroactively. If Acme Corp moves from West to East, the $150,000 booked while Acme was a West account
becomes East revenue in every report, including the ones that were signed off months ago. No query
against the model can reproduce the number that was true in May, and nothing records that it ever was.

**Use it when** the change is a correction — a misspelled name, a mistyped industry, a data-entry fix.
A correction should not create a version, because the old value was never true.

### Type 2 — add a new version

The change creates a *second row* for the same entity, and each fact joins to the version in force
when the fact happened. This is the workhorse.

It requires three things that Type 1 does not:

- **A surrogate key.** The business key — `A-001` — now identifies several rows, so the fact cannot
  point at it. The fact points at a model-owned surrogate key that identifies one specific *version*.
  The business key stays on the dimension as the durable key you group by when you want the entity
  rather than the version.
- **Effective dating.** `effective_from`, `effective_to` and usually an `is_current` flag, so that
  "as at" queries and "current state" queries are both cheap.
- **Version resolution at load time.** Something has to decide, for each incoming fact, which version
  was in force on the event date. That is the builder's job, and getting it wrong is one of the most
  common serious modeling bugs there is — see the note on late-arriving facts below.

**Use it when** the change is an event you will be asked to report on: territory moves, segment
reclassification, ownership changes, price-band changes.

The costs are real and worth stating. The dimension grows — a volatile attribute on a large dimension
can multiply row counts. Counting dimension rows no longer counts entities, so a distinct count on the
durable business key becomes mandatory. And "current" reporting requires everybody to remember the
`is_current` filter, which is an argument for exposing current-state through a governed view rather
than trusting discipline.

### Type 3 — add a column

Keep one row, and add a column for the previous value: `region` and `previous_region`. No effective
dates, no extra rows.

This supports exactly **one** look-back, and it collapses the second time the attribute changes. That
narrowness is occasionally exactly right: a single reorganization where the business genuinely needs
every number reported both ways — old territory and new territory, side by side — for a transition
period. It is cheap and it is honest about its limits.

**Use it when** there is one known, bounded change and the requirement is "show me both", not "show me
history".

### Type 4 — split the volatile attributes out

When a dimension has a handful of fast-changing attributes and a great many stable ones, Type 2 on the
whole dimension is wasteful: every change to one volatile attribute versions the entire row.

Type 4 splits them. The volatile attributes move into a small separate dimension — a **mini-dimension**
— holding one row per *combination* of banded values, and the fact carries a key to both. Because the
volatile attributes are typically banded (a credit-score band rather than a score, a size band rather
than a headcount), the mini-dimension stays small and stops growing.

The name is also used for the related pattern of keeping the main dimension current-only and moving the
version history to a separate history table. Both are the same instinct: stop making the primary
dimension carry a cost it does not need.

**Use it when** a few attributes change often, and especially when their values are naturally banded.

### Type 6 — the hybrid

Sometimes called 1+2+3. Type 2 rows for history, plus a column on every row carrying the *current*
value of the attribute. One join then answers both questions: group by the versioned column for "as
was", group by the current column for "as is".

This is genuinely useful — "show me last year's sales under this year's territory alignment" is a real
and frequent request — and it is more maintenance, because every version of every row has to be updated
when the current value changes.

### What to actually ask

The technical taxonomy is downstream of one business question, and it is worth asking in these words:

> **When this attribute changes, should last quarter's report change with it?**

"Yes, obviously, we always want the current view" is Type 1, or Type 6's current column. "No, last
quarter's report should still reconcile" is Type 2. "Both, and I need to compare them" is Type 6, or
Type 3 if it happens once.

| | History preserved | Prior reports reconcile | Rows per entity |
|---|---|---|---|
| Type 0 | Original only | Yes, for the original | 1 |
| Type 1 | No | No | 1 |
| Type 2 | Full | Yes | One per version |
| Type 3 | One step back | Partly | 1 |
| Type 4 | Full, in the mini-dimension | Yes | 1 in the base dimension |
| Type 6 | Full, plus current | Yes, both ways | One per version |

Two practical notes. First, in Salesforce, **field history tracking is not a slowly changing
dimension** — it is an audit log, with different retention, coverage and shape. Turning it into a Type 2
dimension is real ETL work, not a configuration setting. Second, decide this per *attribute*, not per
dimension. Most real dimensions are a mixture: a Type 1 name, a Type 2 region, a Type 0 acquisition
date, all on the same table.

---

## The date dimension

Referenced from [Part 1](../session-1-facts-and-dimensions.md) and
[Part 7](../session-7-modeling-for-the-agent.md).

Every model in this series draws a `Date` box and moves on. It deserves better, because the date
dimension is the one table where a small amount of modeling discipline prevents a disproportionate
number of arguments.

### Why you materialize a calendar table

You could derive year, quarter and month from a date column with functions. There are four reasons not
to.

**Rows for dates with no facts.** A calendar table has a row for every date in range whether or not
anything happened. That is what lets a monthly trend show a zero for a month with no orders instead of
skipping it — and a line chart with a missing month is a chart that lies by omission. This is the same
argument as driving a whitespace report from the `Account` dimension rather than from a fact: absence is
only visible if something represents it.

**Attributes computed once.** Fiscal year, fiscal quarter, period labels and week numbers get defined
in one place. The alternative is the same date arithmetic reimplemented in a dozen calculated fields,
which will eventually disagree with itself — and the disagreement will surface as two dashboards
showing different quarters.

**Attributes that cannot be derived at all.** This is the decisive one. A 4-4-5 retail calendar, a
52/53-week fiscal year, trading days, holiday calendars, a company's own week-numbering — none of these
can be computed from a date with arithmetic. They are lookups. Once you need one, you need the table,
and you may as well have built it from the start.

**Cost.** A calendar table for a decade is a few thousand rows. It is the cheapest join in the model.

The series dataset builds one deliberately: `data/calendar.csv` runs from 1 October 2025 to 31 January
2027 — wider than the facts on purpose, so the boundary cases exist to be tested.

### Fiscal against calendar

The dataset's fiscal year starts on **1 February**. That single choice produces the whole Part 7 trap:
as at 25 August 2026, calendar year-to-date bookings are $600,000 and fiscal year-to-date bookings are
$480,000, because Delta Foods' order `R-006` was placed on 20 January 2026 — inside the calendar year,
before the fiscal year began. A $120,000 gap, 20% of the number, from one order and one convention.

The same fault line runs through the pipeline fact independently. Closed-won opportunity value is
$400,000 on the calendar year and $320,000 on the fiscal year, because `O-006` closed on 16 January
2026. Note that this is *closed-won value*, not "bookings" — in this model bookings always means
orders, and using one word for both is precisely the governance failure Part 7 is about.

Two things go wrong around fiscal calendars more than anything else.

**The labeling convention is ambiguous and nobody documents it.** A fiscal year running February 2026
to January 2027 is called FY2026 by some organizations and FY2027 by others, depending on whether the
label follows the start or the end. The dataset labels by the year the fiscal year ends in, so February
2026 through January 2027 is FY2027 and January 2026 belongs to the previous fiscal year. Neither
convention is more correct. Both are catastrophic when two systems disagree silently, so write the
convention into the model and not into a wiki — which is why it appears as
`fiscal_year_naming: ending_year` in
[the model specification](../Semantic%20Models/sales-pipeline-model.yaml), sitting beside the
fiscal start month rather than living in someone's memory.

**A fiscal calendar is data, not a constant.** Organizations acquire other organizations, and the
acquired unit's fiscal year does not change to be convenient. A fiscal year hardcoded into a metric
definition is a defect waiting for an acquisition; a fiscal year resolved from the calendar table, per
business unit, is not. That is the difference between standardizing and overfitting.

### Role-playing

One physical calendar, related more than once. In the series model the calendar plays three roles:
`created_date` and `close_date` on `Opportunity`, `order_date` on `Order`.

Two rules make this work:

- **Do not build three calendar tables.** They will drift, and three tables mean three definitions of
  "fiscal quarter" — the exact problem materializing a calendar was supposed to solve.
- **Name the relationship for the role, not the table.** "Created Date" and "Close Date", never "Date"
  twice. A person choosing fields from a picker that offers `Date` twice is choosing at random, and so
  is an agent.

The stakes are not subtle. In the dataset, two opportunities worth $180,000 were created in 2025 and
*none* closed in 2025 — so "how much did we do last year" is either $180,000 or nothing, depending
entirely on a role nobody stated.

### What flags like `is_fiscal_ytd` buy you

The dataset's calendar carries `is_calendar_ytd` and `is_fiscal_ytd`. Materialized boolean flags like
these buy three real things:

- **One filter, no arithmetic.** "Year to date" becomes `is_fiscal_ytd = TRUE` rather than a date
  expression involving the current date and a fiscal offset, computed slightly differently in each
  place it appears.
- **A single definition everyone shares.** The flag is a column, so there is exactly one answer, and
  the two competing answers become two visibly different columns rather than one ambiguous phrase.
- **Something you can point an agent at.** A boolean column with a clear description is much harder to
  misuse than an instruction to reason about fiscal periods.

They cost you two things, and both are worth knowing before you commit.

**A flag encodes a moment, so it goes stale.** `is_fiscal_ytd` is true relative to an "as at" date, and
the day after you build it, it is wrong. It must be rebuilt on a schedule, and a stale flag fails
*silently* — the number is simply a day or a week behind, which is the hardest kind of error to notice.
Anything that depends on a refreshed flag needs monitoring.

**Flags multiply.** Year to date invites last year to date, current quarter, prior quarter, rolling
twelve months, same period last year. Twenty boolean columns is its own navigation problem.

The usual answer to the second cost is **offset columns** alongside the flags: `day_offset`,
`month_offset` and `fiscal_period_offset`, each measuring distance from the current period, so that zero
is now, −1 is the previous period and a range expresses "the last 90 days" or "the same quarter last
year" without a new column per question. Offsets need the same daily refresh as flags, but a handful of
them replace dozens.

For a 4-4-5 or 52/53-week calendar this stops being a convenience and becomes the only workable
approach. "The same week last year" is not a date-arithmetic operation on those calendars — it is a
lookup, and the calendar table is the only place it can live.

---

## Referential integrity and orphan handling

Referenced from [Part 2](../session-2-relationships-vs-joins.md).

**Referential integrity** is the property that every foreign key on a fact points at a row that
actually exists in the dimension. It is worth separating two things that are routinely conflated:
integrity that is *declared*, which is a promise the modeler makes and the engine may act on, and
integrity that is *enforced*, which is a constraint the data genuinely satisfies. Declaring integrity
that the data does not have is how orphan rows become invisible rather than absent.

### The semantics, precisely

Four behaviors, and it is worth being able to state them without hedging.

- **Inner.** Keep only rows that match on both sides. Orphan facts are dropped *and* dimension members
  with no facts are dropped. Both losses are silent.
- **Left outer from the fact.** Keep every fact row; dimension attributes are null where there is no
  match. Measure totals are preserved, and orphans collect in a null bucket.
- **Left outer from the dimension.** Keep every dimension member; measures are null where there are no
  facts. This is the direction whitespace reporting needs, and it is the direction people forget
  exists.
- **Full outer.** Keep both. Necessary when aligning two aggregated facts, because either fact may have
  keys the other lacks.

Two consequences are easy to miss.

**A sum over zero rows is null, not zero.** In a dimension-driven report, an account with no orders
shows blank rather than $0 unless you say otherwise. That is not cosmetic: a filter such as
"bookings < 50,000" will typically not match a null, so the accounts you most wanted to find drop out of
the very report designed to find them. Decide explicitly whether absence means zero or unknown, and
coalesce where it means zero.

**In a relationship-based semantic model you rarely choose a join type directly.** The engine picks
based on which fields the question references — that is the economical-query behavior from Part 2.
What you control is upstream of that: whether unmatched keys can exist at all, what happens to them at
load time, and whether your report is driven by the dimension or by a fact. Those three decisions
determine whether a row can vanish, regardless of what the planner does.

The dataset shows both failure modes at once. A naive inner join between `Orders` and `Opportunities`
through `Account` drops Granite Bank ($55,000 of orders, no opportunities) and Cyan Systems ($75,000
open, no orders). Aggregating each fact and aligning them with a full outer join recovers both — but
still cannot show Helios Energy, Ionic Labs and Juniper Retail, which have no facts at all and exist
only in the `Account` dimension. **A full outer join between two fact summaries cannot invent a key that
is in neither of them.**

### The Unknown member pattern

The fix for orphans is not a join type. It is a deliberate dimension row.

Create explicit, described members in every conformed dimension — an "Unknown Account", and usually
"Not Applicable" as well — on reserved keys, and route unmatched fact keys to them during load. The
properties this gives you are worth the effort:

- **Totals stay constant.** Adding a dimension to a view no longer changes the grand total, which
  removes an entire class of "the number moved when I added a column" confusion.
- **Breakage becomes visible in the currency executives read.** "$40,000 against Unknown Account" is a
  number on a report that somebody will ask about. A missing $40,000 is not.
- **It becomes measurable.** The value sitting against Unknown members is a data-quality metric you can
  trend, alert on and hold somebody accountable for.
- **It is describable.** Unlike a null bucket, an explicit member is a real dimension row with a name
  and a description, so it can be filtered, counted and explained to an agent.

Distinguish the reasons for routing there, using separate members rather than one bucket: a key that is
genuinely absent, a key that is not applicable, and a key whose dimension row has not arrived yet.
They have different owners and different fixes, and one bucket hides that.

### Late-arriving dimensions

A fact arrives before the dimension row it references — a new account created in one system and
replicated on a different schedule from the opportunity booked against it. Three options, in order of
preference:

1. **Inferred members.** Insert a stub dimension row carrying the business key with attributes marked
   unknown, and let the fact join to it immediately. When the real record arrives, update the stub in
   place, Type 1 style. The fact never needed to move, and no revenue was ever hidden. This is the
   right default.
2. **Quarantine and reprocess.** Hold the fact aside and load it once the dimension exists. Correct,
   and it keeps the model clean — but the fact is missing from reports in the meantime, so the
   quarantine needs to be visible and monitored, or it becomes a place data goes to die.
3. **Route to Unknown permanently.** Simplest, and it loses the link for good. Acceptable only for keys
   you have concluded will never resolve.

The related bug is worse and much more common: a **late-arriving fact against a Type 2 dimension**. A
fact whose event date is three months ago must join to the dimension version in force *three months
ago*, not to the current version. Loading it against the current version quietly misattributes it — and
because the total is right, nothing looks wrong. Any load process that assigns surrogate keys by
"current version" rather than "version as at the event date" has this defect, and it will not surface
until somebody reconciles a historical report and cannot.

One last case: **retroactive orphans.** A dimension row deleted upstream turns every existing fact
pointing at it into an orphan, and totals that reconciled last month stop reconciling with no change to
the facts at all. Prefer soft deletes on dimensions, and keep the row with a status attribute rather
than removing it.

---

## Additivity

Referenced from [Part 5](../session-5-calculated-fields-that-scale.md).

Additivity is the question of **which aggregations of a measure are legitimate** — as distinct from
which ones the engine will let you perform, which is nearly all of them.

The first thing to get right is that additivity is a property of a **measure and a dimension together**,
not of a measure alone. Headcount is perfectly additive across departments and completely
non-additive across months. Saying "headcount is semi-additive" is shorthand for "additive over every
dimension except time", and time is the usual exception because time is where snapshots live.

### Additive

Summable across every dimension in the model. Flows: amounts, quantities, counts of events. Order
amount is additive — $600,000 is $600,000 whether you group it by account, by month, by product, or not
at all, and the parts always reconstruct the whole.

Most currency measures on a transactional fact are additive, and this is the case that needs no
thought. It is also the case people assume they are in when they are not.

### Semi-additive

Additive across every dimension except time, because each period's value is a **stock** — a complete
statement of a position at a moment — rather than a flow accumulated over the period. Headcount,
inventory on hand, account balance, contract value in force, open pipeline as at a date.

Sum across accounts and you get a meaningful total. Sum twelve monthly snapshots and you have counted
every person, every unit and every dollar twelve times. That is the
[several times too high](symptom-triage.md#headcount-or-balance-reads-several-times-too-high) symptom,
and it is the single most common wrong number in financial and operational reporting.

Across time you need a rule, and which rule is a **business** decision, not a technical default:

- **Period end (last).** The closing position. Right for a balance sheet, a headcount report, a
  month-end inventory figure.
- **Period start (first).** Occasionally right for opening-balance reporting and reconciliations.
- **Period average.** Right when the measure is consumed as a rate — average daily balance for
  interest, average headcount for cost per head, average inventory for turnover.
- **Maximum.** Right for capacity and peak-usage questions.

Two implementation notes. If the measure comes from a **periodic snapshot fact** — one row per entity
per day or per month — then the discipline is that a query must always constrain to a single snapshot
date unless it is deliberately doing a trend, and the model should make that hard to forget. And the
time rule belongs in a governed metric, so that the correct aggregation is the *only* one on offer
rather than the one people are supposed to remember.

### Non-additive

Cannot be meaningfully summed across anything. Recompute from the components instead.

- **Ratios, rates and percentages.** Win rate, margin percentage, conversion rate, coverage. The
  arithmetic of the aggregate is not the arithmetic of the parts: divide numerator by denominator at
  whatever level you want the answer, never combine the ratios. The four owner-level win rates in the
  dataset average to 39.6% while the correct company figure is 40.0%, because the owners carry
  different amounts of closed value.
- **Averages.** `AVG` is non-additive for the same reason, and the failure is sharper than people
  expect: the average of averages equals the true average only when the groups are exactly equal in
  size. Store the sum and the count as additive measures, and divide at the display level.
- **Distinct counts.** Distinct accounts in Q1 plus distinct accounts in Q2 does not equal distinct
  accounts in the half-year, and no correction factor exists, because the overlap is data-dependent.
  Recompute a distinct count at the level you intend to show it.

The mechanics in Tableau Next follow directly. A ratio expressed as `SUM(...) / SUM(...)` is finished
arithmetic, so its aggregation type must be `UserAgg` or the engine will double-aggregate it and the
result will be wrong — usually visible as
[a percentage over 100](symptom-triage.md#a-percentage-metric-exceeds-100), or as a rate that drifts as
you change the grain of the view.

Note in passing that `MIN` and `MAX` are the well-behaved exceptions among non-sums: the maximum of the
per-group maxima *is* the overall maximum, so they combine safely even though they are not sums. It is
`SUM`, `AVG` and `COUNT DISTINCT` that need the care.

### The design conclusion

Classify each measure once, record it in the model, and then **make the illegal aggregation
unavailable**. Expose semi-additive measures through a metric that applies the time rule; expose ratios
through a metric that recomputes from components. Additivity enforced by documentation is additivity
that will be violated by the third person who touches the model. Additivity enforced by the metric
definition cannot be.

---

## Degenerate and junk dimensions

Not covered in the narrative. Both are relevant from
[Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md) onwards, once you are modeling at line
grain.

Two small patterns that resolve a disproportionate amount of confusion about "where does this column
go".

### Degenerate dimensions

A **degenerate dimension** is a dimension attribute that lives on the fact row itself, because it has no
attributes of its own and therefore nothing to build a dimension table around. Order numbers, invoice
numbers, ticket numbers, opportunity ids.

They arise naturally and unavoidably. When you model at line grain, the identifier of the parent
operational document comes along for the ride — and once its descriptive attributes have been
distributed to proper dimensions, the identifier is all that is left. There is nothing to join to
because there is nothing left to look up.

In the dataset, `order_id` is degenerate at order-line grain and `opportunity_id` is degenerate at
line-item grain. They are genuinely useful there:

- **Grouping.** "Revenue per order" needs the order identifier at line grain.
- **Distinct counting.** "How many orders" at line grain is a distinct count of `order_id`. This is the
  fix for the [inflated count](symptom-triage.md#counts-are-inflated-but-the-sums-are-correct) symptom —
  11 order lines, 9 orders.
- **Drill to detail and audit.** The identifier is how a number on a dashboard gets traced back to a
  record in the operational system, which is what makes a figure defensible in a way no amount of
  modeling can.

Three things to watch. Do not build a single-column dimension table for tidiness — a table whose only
column is its own key adds a join and nothing else. Do not confuse a degenerate dimension with a
*descriptive attribute sitting on a fact*: `opportunity_name` on the opportunity fact is not a
degenerate dimension, it is an attribute, and if you find several of them clustered together you have
probably found a dimension that was never built. And remember that a degenerate dimension is as
high-cardinality as the fact itself, so putting one in a view produces a row per document — fine for
detail, fatal for a summary.

### Junk dimensions

A **junk dimension** collects several low-cardinality flags and indicators into one small dimension,
holding one row per combination, so the fact carries a single key instead of a swarm of columns.

The problem it solves is familiar. A fact accumulates a dozen booleans and short codes — is renewal, is
discounted, payment method, delivery type, order channel, priority. Individually each is trivial.
Collectively they widen the fact, and they present anybody navigating the model — or any agent reading
it — with twelve columns that all look like metadata and none of which is described.

The construction is mechanical. Enumerate the combinations, either the full Cartesian product or only
the combinations that actually occur, give each one a surrogate key, and put descriptive labels on it.
Four attributes with 3, 2, 2 and 5 valid values is at most 60 rows — a dimension small enough to be
free.

What you gain: one key on the fact instead of twelve columns; one place where the labels are defined,
so "R" becomes "Renewal" once rather than in every view; and a single object where an agent can find the
whole family of order characteristics with descriptions attached.

What you pay: filtering on a single flag now goes through the junk dimension rather than reading a
column on the fact, which is a small indirection but a real one for ad-hoc users who expected the field
where it used to be. And the combination table has to be extended when a new valid value appears, which
is a load-time responsibility somebody must own.

**When not to bother.** One or two flags — leave them on the fact. Flags that users filter
independently and firmly expect to see as separate fields — the ergonomic cost outweighs the tidiness.
Anything with meaningful cardinality — that is not junk, it is a dimension, and it should be modeled
as one.

---

## A note on terminology: fan trap and chasm trap

Referenced from [Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md).

The series uses "fan trap" and "chasm trap" because they are useful, memorable names for two distinct
mechanisms. Be aware that the literature does not agree with itself, so a reader who goes looking will
find the same words used for different things. The mechanisms are stable; the labels are not.

**Where the terms come from.** "Fan trap" and "chasm trap" belong to the relational-universe tradition,
and they are standard vocabulary in BusinessObjects universe design, where the prescribed remedies are
aliases and contexts — the universe designer's way of forcing each measure down a single join path so
it cannot be multiplied by another. If you meet the terms in a semantic-layer or reporting-tool context
with a strong opinion about how to fix them, this is usually the tradition talking.

**Kimball uses a different vocabulary for the same ground.** The dimensional-modeling literature —
*The Data Warehouse Toolkit* and its successors — does not lean on those two labels. It prescribes the
behavior instead: do not join two fact tables directly; aggregate each fact separately and combine the
results across conformed dimensions, which is **drill-across**. For genuine many-to-many it uses
"multi-valued dimension", "bridge table" and "allocation factor". A reader fluent in Kimball may
recognize every mechanism in Part 3 and none of the names.

**Tableau's own framing is different again.** Tableau's relationship model — introduced in Tableau
2020.2 and conceptually the same idea as the relationships in a Tableau Next semantic data model —
describes the problem as measures being aggregated at their **own level of detail** rather than as a
pair of named traps. The point of relationships is that each measure is aggregated at the grain of its
own table before the results are combined, which is why relationships avoid the duplication that a
physical join produces. A Tableau-native reader may therefore have internalized the *solution* without
ever meeting the vocabulary for the *problem*.

**Where the confusion actually bites.** Three overlaps are worth knowing about:

- Some sources use "fan trap" for **any** one-to-many inflation — what this series calls fan-out —
  while others reserve it specifically for the two-consecutive-one-to-many chain.
- Some use "fan trap" loosely for the two-facts-one-dimension case that others firmly call the chasm
  trap. If somebody says "fan trap" and describes two fact tables, they mean the chasm trap.
- "Chasm trap" is variously described as producing a Cartesian product, a partial Cartesian product, or
  a many-to-many between two facts. All three descriptions are pointing at the same behavior: rows
  paired within each shared key value.

**The practical advice: describe the mechanism, not the label.** Two sentences travel across every
vendor and every textbook, and they will get you understood in any room.

> "This measure lives at a coarser grain than the rows in the view, so it is being repeated and then
> summed."

> "These two facts share a dimension but not a grain, so the engine is pairing their rows."

If you can say which of those two is happening, and produce the row arithmetic — three orders and three
opportunities for Acme Corp make nine rows, $600,000 of bookings read as $1,245,000 — the name you give
it is a matter of local dialect.
