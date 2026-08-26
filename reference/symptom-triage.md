# Symptom Triage

*A diagnostic lookup keyed by what you actually observe — find the symptom, get the likely cause, the
check to run, and the fix.*

Back to [the series overview](../README.md).

Nobody arrives at a modeling problem holding a diagnosis. They arrive holding a symptom: a number
that is too big, a filter that did nothing, two dashboards that disagree. This file is organized the
way the problem actually presents itself.

---

## The two-minute triage

Before you look anything up, answer these four questions in order. They resolve most cases on their
own.

1. **Is the number too big, too small, or just different from another number?** Too big means
   duplication. Too small means something was dropped. Different means context.
2. **What is the grain of every object in the view?** Write down "one row per ___" for each. A total
   that is too big almost always has two grains in it.
3. **Is the measure additive?** If it is a ratio, a rate, a percentage or a snapshot, most of the
   arithmetic you would like to do to it is illegal.
4. **Did the query even visit the object you are blaming?** If nothing in the view references it, it
   was never touched.

---

## Index

| Family | Symptom | Likely cause | Part |
|---|---|---|---|
| Too big | [A total is two or three times too big](#a-total-is-two-or-three-times-too-big) | Fan-out, or a chasm trap between two facts | [3](../session-3-grain-fan-out-and-the-chasm-trap.md) |
| Too big | [Revenue by product exceeds total revenue](#revenue-by-product-exceeds-total-revenue) | All-or-nothing attribution across a bridge | [4](../session-4-conformed-dimensions-junctions-whitespace.md) |
| Too big | [Counts are inflated but the sums are correct](#counts-are-inflated-but-the-sums-are-correct) | Rows counted after a fan-out the measure was protected from | [3](../session-3-grain-fan-out-and-the-chasm-trap.md) |
| Too big | [Headcount or balance reads several times too high](#headcount-or-balance-reads-several-times-too-high) | A semi-additive measure summed across time | [5](../session-5-calculated-fields-that-scale.md) |
| Too big | [A percentage metric exceeds 100](#a-percentage-metric-exceeds-100) | A ratio re-aggregated, or grains that do not match | [5](../session-5-calculated-fields-that-scale.md) |
| Too small | [Rows are missing from a total](#rows-are-missing-from-a-total) | Inner-join semantics dropping orphans or single-fact keys | [2](../session-2-relationships-vs-joins.md), [4](../session-4-conformed-dimensions-junctions-whitespace.md) |
| Too small | [A total got smaller after you added a field](#a-total-got-smaller-after-you-added-a-field) | The new field forced a traversal, and the traversal drops non-matches | [2](../session-2-relationships-vs-joins.md) |
| No effect | [A filter changes nothing](#a-filter-changes-nothing) | The query never traveled to the filtered object | [2](../session-2-relationships-vs-joins.md) |
| Different | [Two dashboards disagree on the same metric](#two-dashboards-disagree-on-the-same-metric) | Different filter placement, so different denominators | [6](../session-6-order-of-operations-and-context.md) |
| Different | [The grand total is not the sum of the displayed rows](#the-grand-total-is-not-the-sum-of-the-displayed-rows) | A non-additive measure correctly recomputed at the total level | [5](../session-5-calculated-fields-that-scale.md), [6](../session-6-order-of-operations-and-context.md) |
| Different | [Percent of total percentages look wrong](#percent-of-total-percentages-look-wrong) | The denominator is the total of whatever is in context | [6](../session-6-order-of-operations-and-context.md) |
| Changed | [A number changed retroactively for a closed period](#a-number-changed-retroactively-for-a-closed-period) | A Type 1 overwrite on a dimension attribute | [1](../session-1-facts-and-dimensions.md) |
| Slow | [A dashboard got slow after adding one field](#a-dashboard-got-slow-after-adding-one-field) | A row-level calculation on a leaf object reaching across hops | [5](../session-5-calculated-fields-that-scale.md) |
| Agent | [The agent picks the wrong measure](#the-agent-picks-the-wrong-measure) | Look-alike fields with no descriptions and no governed metric | [7](../session-7-modeling-for-the-agent.md) |
| Agent | [The agent and finance disagree about this year](#the-agent-and-finance-disagree-about-this-year) | Fiscal versus calendar, decided by guess rather than by model | [7](../session-7-modeling-for-the-agent.md) |

---

## Too big

### A total is two or three times too big

> "Bookings on my dashboard say $1.2 million. Finance says $600,000. Nobody typed anything wrong."

**Likely cause.** Duplication from mixed grain. Two shapes produce it. **Fan-out** — you aggregated a
measure from the "one" side of a one-to-many, so the parent value was copied onto every child row and
you summed the copies. **The chasm trap** — you put two facts in one view through a shared dimension,
and because they share a dimension but not a grain, every row of one fact was paired with every row of
the other for each dimension member.

**The check.** Query the measure from its own fact with nothing else in the view. If that number is
correct and it inflates the moment you add a second object, you have found the culprit object. Then
count rows: for one dimension member, how many rows does each fact have? Their product is your
inflation. In the dataset, Acme Corp has 3 orders and 3 opportunities, so joining them through
`Account` returns 9 rows for Acme alone and 18 across the whole model — turning $600,000 of bookings
into $1,245,000 and $1,250,000 of opportunity value into $2,150,000.

**The fix.** For fan-out, aggregate the measure that lives at the grain you are displaying — use
`[Opportunity Line Item].[Line Amount]` when the view is at line grain, not
`[Opportunity].[Amount]` — and make sure the relationship's cardinality is declared honestly so the
engine can protect the header measure. For the chasm trap, do not join the facts: aggregate each one
separately at its own grain and align the summaries on the conformed dimension key.

**Covered in** [Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md), with the fix in
[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md).

---

### Revenue by product exceeds total revenue

> "Total revenue is right, but when I break it down by product the column adds up to three times as
> much."

**Likely cause.** All-or-nothing attribution across a bridge. You reported a measure that lives at
the parent grain, grouped by a dimension reached through a junction object, so each product received
the *whole* parent amount rather than its share.

**The check.** Sum the by-product column and compare it against the same measure with no product
dimension in the view. Then check where the measure lives: if the measure is on the parent and the
grouping dimension is reached through a bridge, this is the bug. Opportunity `O-001` is $100,000
across three products; attributing the header amount to each of them reports $300,000.

**The fix.** Report the measure that exists at the bridge's own grain — the line amount, not the
header amount. Where no line measure exists, put an explicit **allocation factor** on the bridge and
multiply by it. For `O-001` the factors by line value are 0.40, 0.35 and 0.25, and they sum to exactly
1.00, which is the property that makes the breakdown reconcile. An equal split would give $33,333 to
each product — simple, defensible, and different; choose it deliberately rather than by accident.

**Covered in** [Part 4](../session-4-conformed-dimensions-junctions-whitespace.md).

---

### Counts are inflated but the sums are correct

> "The amounts tie out perfectly, but it says we have 16 opportunities and we have 11."

**Likely cause.** The semantic layer protected the *measure* from fan-out but you asked it to count
*rows*, and the rows in question are child rows. A count is a measure too, and it inflates by exactly
the fan-out factor.

**The check.** Compare a plain count against a distinct count of the entity key. In the dataset,
counting rows at line-item grain gives 16; counting distinct `opportunity_id` gives 11. If the two
disagree, the view is at a finer grain than the thing you are counting.

**The fix.** Count distinct on the entity's own key, or move the count to a view laid out at that
entity's grain. Beware that a distinct count is not additive across dimensions either — the distinct
counts of two regions do not sum to the distinct count of both unless nothing is shared.

**Covered in** [Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md).

---

### Headcount or balance reads several times too high

> "Year-to-date headcount says 4,200. We have 350 people."

**Likely cause.** A **semi-additive** measure summed across time. Headcount, inventory on hand,
account balance and open pipeline as at a date are all *stocks*, not *flows*: each period's value is a
complete snapshot, so adding twelve monthly snapshots counts every person twelve times.

**The check.** Does the number scale with the number of periods in the view? Show it by month and then
change the date range: if the total moves in proportion to the number of months, it is being summed
across time. 350 people over twelve months reading as 4,200 is the signature.

**The fix.** Sum across every dimension *except* time; across time take the period-end value, or the
period average if that is the business meaning. Declare the measure's additivity in the model so
nobody has to remember, and consider hiding the raw column behind a metric that aggregates it
correctly.

**Covered in** [Part 5](../session-5-calculated-fields-that-scale.md) and
[Going Deeper](going-deeper.md#additivity).

---

### A percentage metric exceeds 100

> "Win rate is showing 340%."

**Likely cause.** Two candidates, and they are easy to tell apart. Either the ratio expression was
**double-aggregated** — the calculation already contains `SUM(...) / SUM(...)`, which is finished
arithmetic, and the engine aggregated the finished results again across groups — or the numerator and
denominator are computed at **different grains**, so one of them fanned out and the other did not.

**The check.** Put the numerator and the denominator on screen as separate columns. If both look right
and only the ratio is wrong, it is re-aggregation: in Tableau Next, check that the calculated field's
aggregation type is `UserAgg`, which is required for any expression that already contains an
aggregation. If the numerator itself is inflated, it is a grain mismatch — find which side crosses a
one-to-many that the other does not.

**The fix.** Set `UserAgg` on ratio calculations. For a grain mismatch, pin both sides to the same
stated grain, with an LOD expression if the view will not cooperate:
`{ FIXED [Account].[Account Name] : SUM([Order].[Amount]) }`.

**Covered in** [Part 5](../session-5-calculated-fields-that-scale.md).

---

## Too small

### Rows are missing from a total

> "Granite Bank buys from us every year. It is not on the customer report at all."

**Likely cause.** Inner-join semantics. Two versions of this. A fact row whose foreign key has no
match in the dimension — an **orphan** — disappears from any report that groups by that dimension. And
a multi-fact query restricted to keys present in **both** facts silently discards anything present in
only one.

**The check.** Count distinct keys in the source fact and compare against distinct keys in the
result. Then look specifically for members that exist in one fact only. In the dataset, joining
`Orders` to `Opportunities` through `Account` drops two accounts: Granite Bank, which has $55,000 of
orders and no opportunities, and Cyan Systems, which has a $75,000 opportunity and no orders. Neither
absence produces a warning.

**The fix.** For orphans, route them to an explicit **Unknown member** so a broken key shows up as a
number somebody will question rather than as revenue you cannot see. For multi-fact reporting,
aggregate each fact separately and combine with a full outer join on the conformed key — which
recovers all five accounts that appear in only one fact. Note the remaining subtlety: accounts with
*neither* an order nor an opportunity — Helios Energy, Ionic Labs and Juniper Retail — appear only if
you drive the report from the `Account` dimension itself. A full outer join between two fact summaries
cannot invent a key that is in neither of them.

**Covered in** [Part 2](../session-2-relationships-vs-joins.md) and
[Part 4](../session-4-conformed-dimensions-junctions-whitespace.md), with the patterns in
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling).

---

### A total got smaller after you added a field

> "Total pipeline was $1,250,000. I added industry as a column and it dropped."

**Likely cause.** Adding the field forced the query to travel to another object — that is the point of
an economical query planner — and the traversal excludes rows that do not match. Any fact row with a
missing or unmatched key drops out at the moment the traversal happens, not before.

**The check.** Note the total, add the field, note it again, and take the difference. Then find the
rows accounting for it: group by the new field and look for a null or absent bucket, or compare
distinct key counts before and after. A drop that appears only when a particular object is referenced
identifies the relationship at fault.

**The fix.** Fix the keys upstream where you can. Where you cannot, give the dimension an Unknown
member and route unmatched facts to it, so the total stays constant and the problem becomes visible as
a labeled bucket instead of a silent shrinkage.

**Covered in** [Part 2](../session-2-relationships-vs-joins.md).

---

## No effect

### A filter changes nothing

> "I filtered to Region = West and the total did not move. The filter is right there on the canvas."

**Likely cause.** The query never visited the object the filter lives on. Queries are economical: the
engine will not cross a relationship unless a field in the question forces it to. If every field in
your view lives on `Opportunity`, the planner answers from `Opportunity` and never travels to
`Account` — so an `Account` filter has no rows to act on.

**The check.** List every field in the view and note which object each one lives on. If none of them
is on the filtered object, that is your answer. In the dataset, `SUM([Opportunity].[Amount])` by close
month reads $1,250,000 with or without a West filter; the correct West figure is $675,000, and you
only see it once the query is given a reason to travel to `Account`.

**The fix.** Either bring a field from the target object into the question, or promote the filter into
context so it is evaluated as a constraint on the whole query. Two further flavours are worth ruling
out: the relationship direction may not propagate the filter — a dimension narrows its fact, but one
fact does not silently narrow another — and the cardinality may be declared wrongly, in which case the
engine either refuses to traverse or traverses the wrong way.

**Covered in** [Part 2](../session-2-relationships-vs-joins.md).

---

## Different

### Two dashboards disagree on the same metric

> "Sales says the win rate is 50%. Finance says 32%. Same field, same model."

**Likely cause.** Neither dashboard is broken. They are answering slightly different questions,
because a filter entered the order of operations at a different point — or because one counts deals
and the other weighs value.

**The check.** For any ratio, put the numerator and the denominator on screen separately on both
dashboards. The one that differs tells you what happened. The dataset yields four defensible win rates
from one field name: by value over closed opportunities only, 40.0% ($400,000 of $1,000,000); by value
over all opportunities, 32.0% ($400,000 of $1,250,000); by count over closed only, 50.0% (4 won of 8
closed); by count over all, 36.4% (4 won of 11). An 18-point spread, and nothing is wrong with any of
them.

**The fix.** Pick one definition, define it once as a governed metric with its grain, filters and
context baked in, and repoint both dashboards at it. Where the business genuinely needs the other
definition, publish it as a second, explicitly named metric — not as an accident somebody rediscovers.

**Covered in** [Part 6](../session-6-order-of-operations-and-context.md).

---

### The grand total is not the sum of the displayed rows

> "The four owner rows show 0%, 100%, 27% and 31%. The grand total says 40%. None of those add up."

**Likely cause.** Most often this is correct behavior on a **non-additive** measure. A ratio computed
at the total level is not the sum of the row-level ratios, and it is not their simple average either —
it is a fresh division of the summed numerator by the summed denominator, which weights each row by
size. Those four figures are win rate by value over closed opportunities, per owner. They average to
39.6%; the correct company figure is 40.0%, because the four owners carry $100,000, $200,000, $445,000
and $255,000 of closed value respectively and the total weights them accordingly.

**The check.** Ask whether the measure is a ratio, a rate, a distinct count or a snapshot. If it is
any of those, expect the total to differ and check it against numerator and denominator sums. If the
measure genuinely *is* additive and the total still does not tie, look for two other causes: the total
may be computed over members not displayed, such as rows removed by a top-N or an aggregate filter, or
the row level and the total level may be aggregating over different grains.

**The fix.** For non-additive measures, nothing — but show the numerator and denominator alongside so
the total is self-evidently right. For the other two causes, decide explicitly whether the total should
respect the displayed rows or the full population, and use context to say which.

**Covered in** [Part 5](../session-5-calculated-fields-that-scale.md) and
[Part 6](../session-6-order-of-operations-and-context.md).

---

### Percent of total percentages look wrong

> "The percentages on my regional breakdown add up to 54%."

**Likely cause.** A percent-of-total's denominator is the total of whatever is **in context**. If the
filter that framed your view was applied after the total was established, the numerators are the
filtered rows and the denominator is the unfiltered population — so the column sums to whatever share
the filter happened to leave.

**The check.** Add the percentages up. If they sum to less than 100%, the denominator is bigger than
the displayed set; if they sum to more, the numerators are inflated, and you are looking at fan-out
rather than context. The three West accounts in the dataset hold $675,000 of the $1,250,000 total: with
region in context they read 51.9%, 40.7% and 7.4%, summing to 100%; with region applied as an ordinary
filter afterwards they read 28.0%, 22.0% and 4.0%, summing to 54%.

**The fix.** Decide which total the percentage is *of*, and say so — promote the framing filter to
context if the answer is "of the filtered set", or pin the denominator with an LOD expression if the
answer is "of the whole company regardless of the filter". Both are legitimate; only one is what your
reader assumes.

**Covered in** [Part 6](../session-6-order-of-operations-and-context.md).

---

## Changed

### A number changed retroactively for a closed period

> "March's regional split is different from the March report we signed off in April. The March data
> has not been touched."

**Likely cause.** A **Type 1** slowly changing dimension. Someone updated an attribute on a dimension
row — a region, a segment, an owner, an industry — and because Type 1 overwrites, every historical
fact now groups under the *current* value. The facts did not move; the label on them did.

**The check.** Confirm that the changed figure is a *breakdown by a dimension attribute* rather than a
measure total. If the grand total is unchanged and only the split moved, an attribute was overwritten.
Then look for the change: an audit trail on the dimension, or a comparison against an archived extract.
In the dataset, if Acme Corp moves from West to East on 1 June 2026, a Type 1 overwrite reports all
$200,000 of Acme bookings as East, including the $150,000 that was booked while the account was in the
West.

**The fix.** For attributes you report history by, use **Type 2** versioning: add a row with
effective-from and effective-to dates and route each fact to the version in force at the time. The same
change then reports $150,000 in the West and $50,000 in the East, and last April's report still
reconciles. Keep Type 1 for genuine corrections — a misspelled name should not create a version.

**Covered in** [Part 1](../session-1-facts-and-dimensions.md) and
[Going Deeper](going-deeper.md#slowly-changing-dimensions).

---

## Slow

### A dashboard got slow after adding one field

> "It loaded in two seconds. We added one calculated field and now it takes forty and the tab eats
> memory."

**Likely cause.** The expensive shape, which is four cost multipliers stacked: a **row-level**
calculation, living on a **high-cardinality leaf object**, that **reaches back across several
relationship hops** to gather its inputs, at least one of which is a **one-to-many**. The formula is
small; the work it triggers is the product of all four.

**The check.** For the new field, answer four questions. Is it row-level or aggregate? Which object
does it live on, and how many rows does that object have? How many relationship hops does it cross?
Is any of those hops a one-to-many? Each "worse" answer multiplies the cost, and a one-to-many hop also
puts the *answer* at risk, not just the runtime.

**The fix.** Work down the cost hierarchy. If the value is row-level and stable — a quantity times a
price, a cleaned category, a fiscal-period tag — materialize it upstream as a real column; nothing at
query time beats a column that already exists. If it must stay dynamic and is reused, define it once as
a governed metric at the right grain. Reserve ad-hoc viz calculations for genuine one-offs.

**Covered in** [Part 5](../session-5-calculated-fields-that-scale.md).

---

## Agent

### The agent picks the wrong measure

> "I asked what we sold last quarter and it used the wrong amount field. It did not say which one."

**Likely cause.** Several look-alike fields and nothing to distinguish them. An org typically has
`Amount`, `Expected Revenue`, `ACV`, `TCV`, `Weighted Amount` and a line-level amount as well. To a
human, surrounding context disambiguates. To an agent reading bare column names they are
interchangeable, so it guesses — and guessing between `[Opportunity].[Amount]` and
`[Opportunity Line Item].[Line Amount]` also picks a grain, which is how a wrong-field answer becomes
a wrong-total answer.

**The check.** Ask the agent to state which field and which filters it used, and compare against a
known-good governed number. Then audit the model for measure-like fields with no description. Any
field an agent can reach and cannot distinguish is a future wrong answer.

**The fix.** Descriptions first — they are the highest-leverage metadata there is. One line per
measure, saying what it means and when to use it. Then synonyms, so the words people actually use land
somewhere. Then governed metrics, so the concepts that matter are answered from a definition rather
than improvised. Steer the agent to curated metrics first, and restrict it to the relationships you
declared rather than leaving ambiguous paths lying around.

**Covered in** [Part 7](../session-7-modeling-for-the-agent.md).

---

### The agent and finance disagree about this year

> "The agent says we are at $600,000 year to date. Finance says $480,000. Both are adamant."

**Likely cause.** Fiscal versus calendar, resolved by guess. "This year" is not a fact of nature; it
depends on a fiscal calendar that has to be recorded somewhere. If it is not in the model, the agent
picks one, and it will be wrong for whichever half of the organization means the other.

**The check.** Ask for the date range used, and for the deals included. Then compare against the
calendar table. In the dataset the fiscal year starts on 1 February, so as at 25 August 2026 calendar
YTD bookings are $600,000 and fiscal YTD bookings are $480,000 — a $120,000 gap, 20% of the number,
traceable to exactly one order: `R-006`, which Delta Foods placed on 20 January 2026 inside the
calendar year but before the fiscal year began.

**The fix.** Materialize the fiscal calendar in the date dimension, declare the house default out loud
in the metric's description, and keep the alternative as a named, first-class metric rather than a
forbidden question. Parameterize the fiscal calendar where the organization genuinely varies — an
acquired business unit on a different year is the usual trigger — and cover the phrasings people use, so
"how are we doing so far this year" lands on the same definition as "year to date".

**Covered in** [Part 7](../session-7-modeling-for-the-agent.md).
