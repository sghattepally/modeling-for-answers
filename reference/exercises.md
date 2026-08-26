# Exercises

*Three or four exercises per Part, grounded in the dataset in `data/` so every answer is checkable —
including several "here is a model, what is wrong with it" diagnostics.*

Back to [the series overview](../README.md).

Work these with the CSVs in `data/` open. Answers are collapsed; the reasoning matters more than the
number, so try to get to an answer before you expand one. Figures marked **verified** are asserted by
`data/verify_numbers.py`; the rest are derived from the same CSVs and the arithmetic is shown so you
can check it yourself.

The dataset in one line: 10 accounts, 4 users, 6 products, 11 opportunities, 16 opportunity line items,
9 orders, 11 order lines. The fiscal year starts on 1 February and the series speaks as at 25 August
2026.

---

## Part 1 — Facts, Dimensions & the Shape of Your Data

[Read Part 1](../session-1-facts-and-dimensions.md)

### 1.1 Classify all eight tables

The dataset has eight tables: `accounts`, `users`, `products`, `calendar`, `opportunities`,
`opportunity_line_items`, `orders`, `order_lines`.

**Question.** Sort them into facts, dimensions and bridges, and write the grain of each one as a
sentence beginning "one row per". Two of the eight are harder than they look — which two, and why?

<details>
<summary>Answer</summary>

**Dimensions** — no measures, used purely as context:

- `accounts` — one row per account.
- `users` — one row per user.
- `products` — one row per product.
- `calendar` — one row per date.

**Facts** — an event with a date and a measure:

- `opportunities` — one row per opportunity. 11 rows.
- `orders` — one row per order. 9 rows.

**The two harder ones** are `opportunity_line_items` (16 rows) and `order_lines` (11 rows). They are
both things at once, and that is not a contradiction:

- As a **bridge**, each is the junction that expresses the many-to-many between its parent fact and
  `Product`. One opportunity involves many products; one product appears on many opportunities.
- As a **fact in their own right**, each has its own grain — one row per product per opportunity, one
  row per product per order — and its own measures, `quantity` and `line_amount`.

The reason this matters is the reason Part 3 exists. `line_amount` lives at line grain and
`[Opportunity].[Amount]` lives at opportunity grain, and the whole family of inflated-total bugs comes
from using one where the view calls for the other.

Two details worth noticing. `opportunity_id` on `opportunities` is a **degenerate dimension** when it
appears on the line-item table: you group and drill by it, but there is nothing to join to. And
`calendar` is a dimension you *built* rather than one you were given — that is deliberate, and
[Going Deeper](going-deeper.md#the-date-dimension) explains why.

</details>

### 1.2 Cost out the one big table

Someone proposes flattening opportunities and their line items into a single wide table so the agent
can "figure it out".

**Question.** How many rows does the flat table have? If you then run `SUM(amount)` on the flattened
header amount, what do you get, against a true total of $1,250,000? And why can you not simply divide
the answer by a constant to correct it?

<details>
<summary>Answer</summary>

**16 rows** — one per opportunity line item (verified). The flattening is driven by the finest grain in
the join.

The header amount is copied onto every child row, so `SUM(amount)` totals each opportunity's amount
multiplied by its line count:

| Opportunity | Amount | Lines | Contribution |
|---|---|---|---|
| O-001 | $100,000 | 3 | $300,000 |
| O-002 | $75,000 | 1 | $75,000 |
| O-003 | $75,000 | 2 | $150,000 |
| O-004 | $150,000 | 2 | $300,000 |
| O-005 | $120,000 | 1 | $120,000 |
| O-006 | $80,000 | 1 | $80,000 |
| O-007 | $50,000 | 1 | $50,000 |
| O-008 | $200,000 | 1 | $200,000 |
| O-009 | $175,000 | 1 | $175,000 |
| O-010 | $125,000 | 1 | $125,000 |
| O-011 | $100,000 | 2 | $200,000 |
| **Total** | **$1,250,000** | **16** | **$1,775,000** |

So `SUM(amount)` reads **$1,775,000** against a truth of $1,250,000 — 1.42 times too big.

You cannot divide by a constant because **the inflation factor is per-opportunity, not global**. O-001
is inflated 3x, O-002 is not inflated at all, and the blend depends entirely on which opportunities the
filter happens to leave in the view. Change the filter and the correction factor changes. This is why
fan-out cannot be patched downstream: the only fix is to keep the grains separate, which is exactly
what the flat table threw away.

Note also that the line amounts themselves are fine. They sum to $1,250,000 across all 16 rows, because
every opportunity's lines reconcile to its header. The data was never wrong; the shape was.

</details>

### 1.3 Diagnostic: a model that calls a fact a dimension

A colleague sends you their model. `Opportunity` is the central fact. Hanging off it is
`Opportunity Line Item`, declared as a **dimension** of Opportunity, with `line_amount` exposed as a
dimension attribute. They have also copied `product_name` onto both `Opportunity Line Item` and
`Order Line` as text columns, and dropped the `Product` table entirely — "one less hop".

**Question.** What is wrong, and what specifically becomes impossible?

<details>
<summary>Answer</summary>

**Two separate mistakes, and the second is the expensive one.**

**Mistake one: the line item is not a dimension.** Run Part 1's five-point test. Does it record an
event with a measure? Yes — `quantity` and `line_amount`. Would folding it in duplicate measures? Yes
— that is the whole fan-out story. So it is a fact at line grain, and a bridge to Product. Exposing
`line_amount` as a *dimension attribute* is the concrete symptom: an attribute is something you group
by, so `line_amount` becomes a set of labels — "40000", "35000", "25000" — that nobody can sum. You
have taken the only correctly-grained revenue measure in the model and made it unaggregatable.

**Mistake two: `Product` is no longer conformed.** With `product_name` copied as text onto two
different tables, there is no single Product dimension — there are two independent lists of strings.
That costs you three things immediately:

- **Product whitespace becomes impossible.** "Which products sell but never appear in the open
  pipeline?" is a set difference between two lists of *product keys*. Two independent text columns
  cannot be differenced reliably — "Training Credits" against "Training credits" is a silent miss.
  The verified answer, Gadget and Gizmo with $235,000 of demand and Training Credits forecast but never
  sold, is not derivable from this model.
- **Product attributes have nowhere to live.** `product_family` and `list_price` are attributes of a
  product, not of a line. With no Product table they either get duplicated onto every line — and
  disagree — or they are dropped.
- **The agent loses its cue.** Two columns called `product_name` on two different objects is precisely
  the ambiguity Part 7 warns about.

The "one less hop" argument is also wrong on its own terms. A single hop from a line item to a small
product dimension is one of the cheapest traversals in the model, and it buys conformance — the
property that makes the entire Part 4 payoff possible.

</details>

### 1.4 A dimension attribute changes

Acme Corp (`A-001`) is in the West region and has three orders: $60,000 on 10 February 2026, $90,000 on
22 May 2026 and $50,000 on 14 August 2026. On 1 June 2026 the account is reassigned to the East region.

**Question.** Report Acme's bookings by region under a Type 1 dimension and under a Type 2 dimension.
Which figure is unchanged in both, and which piece of history does Type 1 destroy?

<details>
<summary>Answer</summary>

Acme's total bookings are **$200,000** either way — $60,000 + $90,000 + $50,000. The total is not what
moves. Only the *split* moves.

**Type 1, overwrite.** The region column now reads "East", full stop. Every fact that joins to Acme
groups under East, including the two orders that were booked while the account was in the West:

- West: $0
- East: $200,000

**Type 2, versioned.** A second Acme row is added with effective dates, and each order joins to the
version in force on its order date:

- West (effective to 31 May 2026): $60,000 + $90,000 = **$150,000**
- East (effective from 1 June 2026): **$50,000**

What Type 1 destroys is **the ability to reconcile a prior report**. The West regional review signed
off in May showed $150,000 of Acme bookings. After the Type 1 overwrite, no query against the model can
reproduce that number, and nothing in the model records that it ever was true. That is the exact
mechanism behind the
[retroactively-changed number](symptom-triage.md#a-number-changed-retroactively-for-a-closed-period)
symptom.

The judgment call is not technical. Ask whether the change is a **correction** or an **event**. A
misspelled account name is a correction — overwrite it, Type 1, no history required. A territory move,
a segment reclassification or an owner change is an event you will be asked to report on, so it needs
Type 2. Types 0, 3 and 4 cover the rest of the space and are in
[Going Deeper](going-deeper.md#slowly-changing-dimensions).

</details>

---

## Part 2 — Relationships vs. Joins

[Read Part 2](../session-2-relationships-vs-joins.md)

### 2.1 The filter that does nothing

You build a view with one measure, `SUM([Opportunity].[Amount])`, broken out by close month. Total
opportunity value is $1,250,000 (verified). You add a filter: `[Account].[Region] = West`.

**Question.** What does the total read after the filter is applied, and what *should* the West figure
be? Name two ways to make the view produce the right number, and say which accounts contribute.

<details>
<summary>Answer</summary>

The total reads **$1,250,000** — unchanged. Every field in the view lives on `Opportunity`, so the
economical query planner answered from `Opportunity` and never traveled to `Account`. The filter had
no rows to act on.

The correct West figure is **$675,000**:

| Account | Region | Opportunity value |
|---|---|---|
| Acme Corp (A-001) | West | $100,000 + $150,000 + $100,000 = $350,000 |
| Borealis Ltd (A-002) | West | $75,000 + $200,000 = $275,000 |
| Fjord Logistics (A-006) | West | $50,000 |
| Ionic Labs (A-009) | West | none |
| **West total** | | **$675,000** |

Two fixes:

1. **Give the query a reason to travel.** Put `[Account].[Region]` in the view — as a column, a row or
   a colour. The query now must visit `Account`, and the filter applies.
2. **Promote the filter to context.** Context is evaluated as a constraint on the whole query rather
   than as a last-mile filter on rows that were never fetched.

Notice Ionic Labs. It is a West account with no opportunities at all, so it contributes nothing to the
$675,000 — and it will never appear in an opportunity-driven view no matter what you filter. Finding
accounts like it requires driving the report from the dimension, which is
[exercise 4.3](#43-diagnostic-what-a-full-outer-join-cannot-recover).

</details>

### 2.2 Declare the cardinality, then get it wrong on purpose

You are drawing three relationships: `Opportunity` to `Opportunity Line Item`, `Opportunity Line Item`
to `Product`, and `Opportunity` to `Account`.

**Question.** State the cardinality of each. Then: if you declared the first one as **one-to-one**,
what does `SUM([Opportunity].[Amount])` return for opportunity `O-001` in a view laid out at line-item
grain, and why?

<details>
<summary>Answer</summary>

- `Opportunity` to `Opportunity Line Item` — **one-to-many**. One opportunity, many lines. O-001 has 3.
- `Opportunity Line Item` to `Product` — **many-to-one**. Many lines reference one product; `P-005`
  Support Plan appears on four different opportunity lines.
- `Opportunity` to `Account` — **many-to-one**. Acme Corp has three opportunities.

Declaring the first as **one-to-one** is a lie the engine will believe. Cardinality is how you tell it
whether an aggregation across that relationship needs protecting from duplication; one-to-one says "no
protection needed, there is at most one row on the other side". So the engine sums the header amount
once per row it finds, and it finds three:

$100,000 + $100,000 + $100,000 = **$300,000** (verified), against a truth of $100,000.

This is the most dangerous class of modeling error, because nothing looks broken. The table is
plausible, every source row is correct, and the number is 3x. Many-to-one is the safe case; one-to-many
multiplies; many-to-many cannot be drawn directly at all and needs a bridge.

</details>

### 2.3 One calendar, two roles, two answers

`Opportunity` has both a `created_date` and a `close_date`. Both relate to the same conformed calendar
— two roles of one dimension.

**Question.** It is early 2026 and someone asks "how much did we do last year?" Answer it once by
created date and once by close date, and say which opportunities you counted.

<details>
<summary>Answer</summary>

**By created date, 2025: two opportunities, $180,000.**

- `O-006` "Fjord Gadget Fleet", created 20 October 2025, $80,000
- `O-011` "Acme Services Add-on", created 1 December 2025, $100,000

**By close date, 2025: nothing at all. $0.** The earliest close date in the dataset is 16 January 2026.

Same dimension, same question, same model — two answers three orders of magnitude apart. Neither is
wrong; they answer different questions. "Created" measures pipeline generation; "closed" measures
outcome.

The lesson is that a role-playing dimension makes the date role a **required** part of the question,
not an optional detail. Leave it implicit and two dashboards will quietly choose differently, which is
the [two dashboards disagree](symptom-triage.md#two-dashboards-disagree-on-the-same-metric) symptom
arriving by a different route. Name the relationships for the role, not the table — "Created Date" and
"Close Date", not "Date" twice — so a person picking fields cannot pick blindly. `Order` adds a third
role, `order_date`, to the same calendar.

</details>

### 2.4 Diagnostic: the orphan you cannot see

Suppose an eleventh opportunity, `O-099`, arrives with an amount of $40,000 and an `account_id` that
does not exist in `accounts.csv` — a typo, or an account deleted after the opportunity was created.
True total opportunity value is now $1,290,000.

**Question.** You build "opportunity value by region". What total does it show, and what does the model
tell you about the discrepancy? What would you change so that next time it tells you something?

<details>
<summary>Answer</summary>

It shows **$1,250,000**, split $675,000 West, $370,000 East, $205,000 Central. The $40,000 is simply
absent, and there is no asterisk, no warning and no null row. Grouping by an attribute of `Account`
required a traversal to `Account`, and under inner-join semantics a fact row with no matching dimension
row does not survive the traversal.

The model tells you **nothing**. That is the whole problem: this is a wrong number that looks like a
right number, and it will only be caught if somebody independently knows the total should be
$1,290,000.

The fix is the **Unknown member** pattern. Create an explicit, deliberate row in the `Account`
dimension — "Unknown Account" — and route unmatched fact keys to it during load. The same view then
reads:

| Region | Opportunity value |
|---|---|
| West | $675,000 |
| East | $370,000 |
| Central | $205,000 |
| Unknown | $40,000 |
| **Total** | **$1,290,000** |

Both totals are defensible arithmetic. Only one of them tells you the data has a problem, and it does
so in the currency executives read: a number on a report that should not be there. The alternative —
outer-join semantics with a null bucket — gets you the same visibility, but an explicit member is
better because it is a real dimension row you can describe, filter and count.

Two further cases are worth handling on the way in: a fact key that is genuinely unknown, and a fact
that has simply arrived **before** its dimension row. They deserve different placeholders, and
[Going Deeper](going-deeper.md#referential-integrity-and-orphan-handling) covers both.

</details>

---

## Part 3 — Grain, Fan-out & the Chasm Trap

[Read Part 3](../session-3-grain-fan-out-and-the-chasm-trap.md)

### 3.1 The $100,000 deal that reads as $300,000

Opportunity `O-001` "Acme Platform Expansion" has an amount of $100,000 and three line items: Widget
$40,000, Platform License $35,000, Support Plan $25,000.

**Question.** In a view laid out at line-item grain, what does `SUM([Opportunity].[Amount])` return,
and what does `SUM([Opportunity Line Item].[Line Amount])` return? Which one is a bug, and what exactly
went wrong?

<details>
<summary>Answer</summary>

- `SUM([Opportunity].[Amount])` returns **$300,000** (verified).
- `SUM([Opportunity Line Item].[Line Amount])` returns **$100,000** (verified) — $40,000 + $35,000 +
  $25,000.

The first is the bug, and precisely locating it matters. **No money was added.** The traversal copied
the header amount onto each of the three child rows, and then the aggregation summed the copies. The
source data is impeccable: the header says $100,000, the lines say $100,000, and they agree.

The rule that falls out of this: **use the measure that lives at the grain of your view.** At line
grain, the line amount is the correctly-grained measure. At opportunity grain, the header amount is.
Mixing them is not a rounding problem — it is a category error, and it happens to be invisible.

Two related points. First, a semantic layer with honestly declared cardinality can protect the header
measure here, because it knows `[Opportunity].[Amount]` lives at opportunity grain — that protection is
the thing [exercise 2.2](#22-declare-the-cardinality-then-get-it-wrong-on-purpose) takes away by lying
about cardinality, and the thing [exercise 1.2](#12-cost-out-the-one-big-table) throws away by
flattening. Second, this dataset is friendlier than reality: every opportunity's lines reconcile to its
header exactly. When they do not, you have a third problem on top of the first two, and you need to know
which of the two figures the business considers authoritative.

</details>

### 3.2 The chasm trap, one account at a time

Acme Corp has 3 orders totaling $200,000 and 3 opportunities totaling $350,000. You put bookings and
opportunity value side by side, by account, by relating `Orders` and `Opportunities` through the shared
`Account` dimension and querying both measures in one pass.

**Question.** How many rows does the join produce for Acme? What do the two measures read for Acme?
Then do it for the whole dataset. Finally: which account in the dataset is completely unaffected, and
what does that tell you?

<details>
<summary>Answer</summary>

**For Acme:** 3 orders × 3 opportunities = **9 rows**. Each order's amount appears 3 times and each
opportunity's amount appears 3 times:

- Bookings read $200,000 × 3 = **$600,000** instead of $200,000.
- Opportunity value reads $350,000 × 3 = **$1,050,000** instead of $350,000.

**For the whole dataset:** 18 rows (verified), from the five accounts present in both facts:

| Account | Orders | Opps | Rows | Bookings | Opp value |
|---|---|---|---|---|---|
| Acme Corp | 3 | 3 | 9 | $600,000 | $1,050,000 |
| Borealis Ltd | 2 | 2 | 4 | $200,000 | $550,000 |
| Delta Foods | 1 | 2 | 2 | $240,000 | $295,000 |
| Everest Health | 1 | 2 | 2 | $160,000 | $205,000 |
| Fjord Logistics | 1 | 1 | 1 | $45,000 | $50,000 |
| **Total** | | | **18** | **$1,245,000** | **$2,150,000** |

Against truths of $600,000 and $1,250,000 — inflations of 2.08x and 1.72x (all verified).

**Fjord Logistics is untouched.** It has exactly one order and one opportunity, so 1 × 1 = 1 row and no
duplication at all. That is the most useful observation in the exercise, for two reasons. It explains
why the inflation factor is 2.08x rather than a round number — it is a blend of per-account factors
ranging from 1x to 3x. And it explains why this bug survives spot-checking: pick Fjord Logistics as
your test account and the model looks perfect.

Also notice what is *not* in the table. Granite Bank and Cyan Systems have vanished, which is
[exercise 4.3](#43-diagnostic-what-a-full-outer-join-cannot-recover).

</details>

### 3.3 Name the trap

Three views on the model. For each, say whether it duplicates anything, name the mechanism if it does,
and give the row arithmetic.

- **A.** Group by `[Account].[Account Name]`, measure `SUM([Opportunity].[Amount])`, with
  `Opportunity Line Item` also in the view.
- **B.** Group by `[Account].[Account Name]`, measures `SUM([Order].[Amount])` and
  `SUM([Opportunity].[Amount])` together.
- **C.** Group by `[Product].[Product Name]`, measure
  `SUM([Opportunity Line Item].[Line Amount])`.

<details>
<summary>Answer</summary>

**A — fan trap.** One path, two consecutive one-to-many hops: `Account` → `Opportunity` →
`Opportunity Line Item`. The header amount fans out by the line count of each opportunity. For Acme,
the three opportunities have 3, 2 and 2 lines, so the account's $350,000 reads $300,000 + $300,000 +
$200,000 = $800,000. Across the model this is the $1,775,000 from
[exercise 1.2](#12-cost-out-the-one-big-table).

**B — chasm trap.** Two facts, one shared dimension, no shared grain. There is no row-to-row
correspondence between an order and an opportunity, so the engine pairs every combination within each
account: 18 rows, $1,245,000 and $2,150,000. See
[exercise 3.2](#32-the-chasm-trap-one-account-at-a-time).

**C — no trap.** The measure lives on `Opportunity Line Item` and the grouping dimension is one
many-to-one hop away, on the "one" side. Traversing toward the "one" side does not multiply anything;
each line contributes its own amount exactly once. Product-level line revenue sums to $1,250,000, which
reconciles to total opportunity value.

The general rule: **duplication risk comes from aggregating a measure across a hop that multiplies the
side the measure lives on.** Toward the "one" side is safe. Toward the "many" side is not. Two facts
joined through a dimension are not a hop at all — they are two separate paths being forced to meet,
which is why the fix is a different query shape rather than a different measure.

</details>

### 3.4 Diagnostic: "I related the two facts so we could compare them"

You inherit a model. Someone has drawn a direct relationship from `Orders` to `Opportunities` on
`account_id`, with a comment: "joined on account so we can see pipeline and bookings together".

**Question.** Give three separate reasons this is wrong, and say what should replace it.

<details>
<summary>Answer</summary>

**Reason one: `account_id` is not a key of either fact.** It is a foreign key on both — non-unique on
both sides. A join on a column that is non-unique in both tables is a partial Cartesian product by
construction, not a lookup. 18 rows out of 9 orders and 11 opportunities.

**Reason two: it inflates both measures, unevenly.** $600,000 of bookings reads $1,245,000; $1,250,000
of opportunity value reads $2,150,000. Uneven inflation is worse than uniform inflation because no
single correction factor exists and a well-chosen spot-check passes.

**Reason three: it silently drops rows.** Granite Bank has $55,000 of orders and no opportunities.
Cyan Systems has a $75,000 opportunity and no orders. Under inner-join semantics both disappear
entirely, so the model is simultaneously overstating the accounts it keeps and hiding the ones it
loses. The re-engagement list and the net-new logo list — the two things a revenue leader would
actually act on — are exactly the rows this join deletes.

**What should replace it:** delete the fact-to-fact relationship. Relate each fact independently to the
**conformed** `Account` dimension, and report them with **drill-across** — aggregate each fact
separately at its own grain, then align the two summaries on the account key. Bookings summed among
orders only, pipeline summed among opportunities only, `Account` acting purely as the shared label that
lets you place them side by side. Align with a **full outer join** so accounts present in one fact only
survive.

The tell to remember, for next time: **a relationship between two facts is almost always a mistake.**
Facts relate to dimensions. When two facts need to meet, they meet through conformed dimensions, after
aggregation.

</details>

---

## Part 4 — Conformed Dimensions, Junctions & the Whitespace Payoff

[Read Part 4](../session-4-conformed-dimensions-junctions-whitespace.md)

### 4.1 Split $100,000 three ways, three ways

`O-001` is a $100,000 opportunity spanning three products, with line amounts of $40,000 (Widget),
$35,000 (Platform License) and $25,000 (Support Plan).

**Question.** Produce "opportunity value by product" for this deal under three attribution rules:
equal split, split by line amount, and all-or-nothing. For each, state the total and say which business
question it actually answers.

<details>
<summary>Answer</summary>

| Product | Equal split | By line amount | All-or-nothing |
|---|---|---|---|
| Widget | $33,333 | $40,000 (factor 0.40) | $100,000 |
| Platform License | $33,333 | $35,000 (factor 0.35) | $100,000 |
| Support Plan | $33,333 | $25,000 (factor 0.25) | $100,000 |
| **Total** | **$100,000** | **$100,000** | **$300,000** |

All figures verified. The by-line factors are 0.40, 0.35 and 0.25 and sum to exactly 1.00, which is the
property that makes the breakdown reconcile to the deal.

What each one answers:

- **Equal split** answers "if we had no idea how the value divided, how would we spread it?" It is
  simple, it reconciles, and here it is demonstrably wrong — it credits Support Plan with $33,333 when
  its line says $25,000. Reach for it only when you genuinely have no line-level value.
- **By line amount** answers "how much revenue does each product represent?" It is the right answer
  here, because the line amounts exist and reconcile to the header. In practice you would not even
  compute a factor — you would report `SUM([Opportunity Line Item].[Line Amount])` directly and let the
  bridge's own measure do the work. The allocation factor earns its keep when you must push a *parent*
  measure down, such as a deal-level discount or a header-level probability.
- **All-or-nothing** answers "which products appear in this deal?" — a perfectly good question, and the
  right rule for counting deals or building a product-coverage matrix. As a revenue breakdown it is
  catastrophic: $300,000 of product revenue for a $100,000 deal, which is the
  [revenue by product exceeds total revenue](symptom-triage.md#revenue-by-product-exceeds-total-revenue)
  symptom.

The point is not that one rule wins. It is that a bridge **forces a choice**, and if you do not make it
explicitly the model makes it for you.

</details>

### 4.2 Fill in the whitespace matrix

Cross the ten accounts against two tests: do they have any orders, and do they have any *open*
opportunities? Open stages are Discovery, Proposal and Negotiation.

**Question.** Populate all four quadrants by name, attach a value to each of the two interesting ones,
and say what action each quadrant implies.

<details>
<summary>Answer</summary>

| | Has open pipeline | No open pipeline |
|---|---|---|
| **Has orders** | Acme Corp, Borealis Ltd | Delta Foods, Everest Health, Fjord Logistics, Granite Bank |
| **No orders** | Cyan Systems | Helios Energy, Ionic Labs, Juniper Retail |

All four quadrants verified.

- **Bought before, nothing open** — 4 accounts, **$300,000** of past bookings. This is the
  re-engagement list, and it is the highest-value cell on the grid: these are customers who have
  already proved they will buy and currently have no reason to talk to you. Delta Foods $120,000,
  Everest Health $80,000, Fjord Logistics $45,000, Granite Bank $55,000.
- **Open pipeline, no order history** — Cyan Systems, **$75,000** open. A net-new logo. Worth flagging
  because a first-time buyer needs different treatment from an expansion, and because a forecast that
  mixes the two is less accurate than one that separates them.
- **Both** — Acme Corp and Borealis Ltd. Existing customers with live pipeline. Normal business.
- **Neither** — Helios Energy, Ionic Labs, Juniper Retail. Prospects, not whitespace. Keep the
  distinction: whitespace is demand you can evidence, and there is no evidence here at all.

Every one of these is a **set difference between two conformed facts**. There is no clever measure and
no new data — it is `has orders` minus `has open pipeline`, in both directions. That is the payoff for
keeping two well-grained facts on shared dimensions, and it is unavailable from a flat table, which has
no way to express "in one fact but not the other".

Watch the definition of "open", though. It carries the whole answer. Include Closed Lost in "has
pipeline" and Delta Foods, Everest Health and Fjord Logistics move quadrant. That is a business
decision, and it belongs in a governed metric rather than in each analyst's filter pane.

</details>

### 4.3 Diagnostic: what a full outer join cannot recover

You fix [exercise 3.4](#34-diagnostic-i-related-the-two-facts-so-we-could-compare-them) properly:
aggregate bookings from `Orders` by account, aggregate open pipeline from `Opportunities` by account,
then align the two summaries on the account key.

**Question.** How many accounts appear if you align them with an inner join, and with a full outer
join? Which accounts does the full outer join still miss, and how do you get them?

<details>
<summary>Answer</summary>

- **Inner join: 5 accounts.** Acme Corp, Borealis Ltd, Delta Foods, Everest Health, Fjord Logistics —
  only those present in both facts. This is the same 5 as the chasm-trap join, minus the row explosion:
  the totals are now correct but two accounts are still missing.
- **Full outer join: 7 accounts.** The 5 above, plus Granite Bank ($55,000 of orders, no opportunities)
  and Cyan Systems ($75,000 open, no orders). Five accounts appear in exactly one fact and are
  recovered only by the outer join (verified).
- **Still missing: 3 accounts.** Helios Energy, Ionic Labs and Juniper Retail have neither an order nor
  an opportunity.

This is the subtlety worth internalizing: **a full outer join between two fact summaries cannot invent a
key that is in neither of them.** It unions the keys that exist in the facts, and a dimension member
with no facts at all exists in neither. To see all ten accounts you must drive the query from the
`Account` dimension and outer-join the two fact summaries onto it.

The practical consequence is a question you should ask of any "accounts without X" report: *is this
report driven by the dimension or by a fact?* A fact-driven report can only ever show you accounts that
did something. Every genuinely empty account — the entire "neither" quadrant, and Ionic Labs from
[exercise 2.1](#21-the-filter-that-does-nothing) — is invisible to it. Total-addressable-market
questions are dimension-driven by nature.

</details>

### 4.4 Product whitespace, both directions

Compare products sold — the ones appearing on `order_lines` — against products forecast, meaning the
ones appearing on line items of *open* opportunities.

**Question.** Which products sell but are absent from the open pipeline, and how much demand does that
represent? Which product is in the open pipeline but has never sold? And which product has the widest
gap between what it sells and what is forecast?

<details>
<summary>Answer</summary>

**Sold but absent from open pipeline: Gadget (`P-002`) and Gizmo (`P-003`), $235,000 of demand**
(verified) — Gadget $50,000 + $70,000 = $120,000, Gizmo $60,000 + $55,000 = $115,000. Two products
generating a quarter of a million in bookings that the forecast is entirely blind to. Either nobody is
selling them deliberately any more, or they are being sold without being forecast — and those are very
different conversations.

**In the open pipeline but never sold: Training Credits (`P-006`)** (verified), $15,000 open. Forecast
risk: there is no historical evidence that this product closes.

**Widest gap: Widget (`P-001`).** It is the best-selling product in the dataset at $180,000 of bookings
— $60,000 + $40,000 + $80,000 — and carries only $40,000 of open pipeline. Full comparison:

| Product | Sold | Open pipeline |
|---|---|---|
| Widget | $180,000 | $40,000 |
| Gadget | $120,000 | — |
| Gizmo | $115,000 | — |
| Platform License | $90,000 | $95,000 |
| Support Plan | $95,000 | $100,000 |
| Training Credits | — | $15,000 |
| **Total** | **$600,000** | **$250,000** |

Both totals reconcile to their facts, which is your check that no fan-out crept in: order lines sum to
$600,000 of bookings and open-opportunity lines sum to $250,000 of open pipeline (both verified).

The whole analysis is a full outer join between two product-keyed summaries. It needs one thing to be
true: `Product` must be a **conformed** dimension, joined by key from both facts. With two independent
`product_name` text columns — the model in
[exercise 1.3](#13-diagnostic-a-model-that-calls-a-fact-a-dimension) — none of this is derivable.

</details>

---

## Part 5 — Calculated Fields That Scale

[Read Part 5](../session-5-calculated-fields-that-scale.md)

### 5.1 A ratio of sums against a sum of ratios

You want win rate by value over closed opportunities: won value divided by closed value. Closed Won is
$400,000 across 4 deals; Closed Lost is $600,000 across 4 deals.

**Question.** Compute it as `SUM(won amount) / SUM(total amount)`. Then compute the tempting wrong
version, `AVG(won amount / total amount)` evaluated per deal. Explain why the wrong version lands on the
number it does — the reason is more interesting than the discrepancy.

<details>
<summary>Answer</summary>

**Ratio of sums:** $400,000 / $1,000,000 = **40.0%** (verified).

**Sum of ratios, averaged:** on each closed deal, "won amount" is the amount if the deal was won and
zero if it was lost, and "total amount" is the amount. So the per-deal ratio is exactly **1 for every
won deal and 0 for every lost deal** — the amount cancels. Averaging over 8 closed deals gives 4/8 =
**50.0%**.

And 50.0% is a real, verified number in this dataset: it is win rate **by count** over closed
opportunities. That is the insight. The sum-of-ratios error did not produce noise. It silently
**converted a value-weighted metric into a count-weighted one**, because dividing on each row destroys
the size information before the average can use it. Every deal ends up with equal voting power
regardless of whether it was worth $50,000 or $200,000.

Ten points of difference, and the give-away is that the wrong number is not obviously absurd — it is a
metric somebody uses on purpose, arrived at by accident.

The rule: **ratios, rates and percentages are aggregate calculations.** Sum the numerator, sum the
denominator, divide once. If you find yourself dividing on each row and then averaging, stop and ask
whether you meant a ratio of sums. And if you genuinely want the count-based rate, write it as a count
ratio so the next reader can see that you meant it.

</details>

### 5.2 The aggregation type on a ratio

You define a model-level calculated field for win rate by value over closed opportunities. The
expression is a ratio of two sums, and both sums reference qualified table fields on `Opportunity`.

**Question.** What aggregation type does this field need in Tableau Next, and what goes wrong without
it? What symptom would you see on a dashboard?

<details>
<summary>Answer</summary>

It needs **`UserAgg`**. The rule is mechanical: **any calculated field whose expression already
contains an aggregation must be declared `UserAgg`.** A ratio written as `SUM(...) / SUM(...)` is
finished arithmetic — the aggregation has already happened inside the expression, and there is nothing
left to aggregate.

Without it, the engine treats the expression as something still to be aggregated and
**double-aggregates** it. The output is wrong, and the specific way it is wrong depends on the view,
which is what makes it hard to spot: the number may look plausible at one level of detail and absurd at
another.

The symptom on a dashboard is usually **a percentage that exceeds 100** — or a rate that drifts as you
change the grain of the view, growing as you add rows and shrinking as you remove them. If a
percentage is impossible, check the aggregation type before you check the maths; the maths is often
fine.

A useful habit: name ratio fields so their nature is visible — `Win_Rate_clc` for the calculated field,
`Win_Rate_mtc` when it is published as a semantic metric — and treat "does this expression contain
`SUM`?" as the trigger question for `UserAgg`. Note also the reference conventions: table fields are
qualified, `SUM([Opportunity].[Amount])`, while calculated fields are model-level and referenced
unqualified, `[Win_Rate_clc]`. And never a double underscore.

</details>

### 5.3 Diagnostic: place four calculations, then find the cost bomb

Four values are needed. For each, decide where it should be computed: materialized upstream in ETL,
defined once as a governed metric in the model, or computed ad hoc in a single view.

- **A.** Line revenue on `order_lines`: `[Order Line].[Quantity] * [Product].[List Price]`.
- **B.** Win rate by value over closed opportunities.
- **C.** A fiscal-period label for every date.
- **D.** "Deals over $100,000 owned by Chen Wei", needed once, for a meeting tomorrow.

**Question.** Place each one. Then: one of these four, written the wrong way, is the classic
dashboard-killer. Which, what is the wrong way, and which four cost multipliers stack up?

<details>
<summary>Answer</summary>

- **A — materialize upstream.** Row-level and stable. Quantity times price never changes once the row
  has landed, so computing it on every dashboard load is pure waste. Nothing at query time beats a
  column that already exists. Note that the expression also crosses a hop to `Product`, which is a
  second reason to resolve it once at load time rather than on every query.
- **B — governed metric.** It must stay dynamic, because the answer depends on what is filtered, and it
  is reused everywhere. Define it once, with grain, filters and context settled, so every dashboard and
  the agent share one definition. It is also a ratio, so it is an aggregate calculation and needs
  `UserAgg`.
- **C — materialize upstream, in the date dimension.** Deterministic and reused by everything. It is a
  column on `calendar`, computed once when the calendar is built. Deriving fiscal periods in each
  view's calculations is how "this year" ends up meaning two things.
- **D — ad hoc.** A genuine one-off. Ad-hoc calculations are invisible to everything else and
  impossible to govern, which is fine for something you will not need again. If you find the same
  ad-hoc calculation in five dashboards, it wanted to be a governed metric.

**The dashboard-killer is A, written as a row-level calculated field on `order_lines` that reaches
across relationship hops to fetch the price.** Four multipliers stack:

1. **Row-level** — evaluated once per row rather than once per group. On a real order-line object that
   is tens of millions of evaluations.
2. **On a high-cardinality leaf object** — the finest-grained table in the model, so the row count is
   the worst available.
3. **Reaching across hops** — every evaluation forces a relationship traversal that a local field
   would not need.
4. **Across a one-to-many hop** — if any hop on the path multiplies, fan-out inflates the cost, and
   possibly the answer as well.

The formula is one line. The work is the product of all four factors, which is how "we only added one
calculated field" turns two seconds into forty. Push stable row-level work down to the builder and
reserve query-time calculation for what genuinely must be dynamic.

</details>

### 5.4 Which of these can you sum?

Six measures: order amount; opportunity amount; win rate; open pipeline as at a date; count of
opportunities; distinct count of accounts with an order.

**Question.** Classify each as additive, semi-additive or non-additive, and say how to aggregate it
correctly across time and across accounts.

<details>
<summary>Answer</summary>

| Measure | Class | Across accounts | Across time |
|---|---|---|---|
| Order amount | Additive | Sum | Sum |
| Opportunity amount | Additive | Sum | Sum |
| Win rate | Non-additive | Recompute | Recompute |
| Open pipeline as at a date | Semi-additive | Sum | Period-end value |
| Count of opportunities | Additive as a count of rows | Sum | Sum |
| Distinct accounts with an order | Non-additive | Recompute | Recompute |

- **Additive** measures are flows. $600,000 of bookings is $600,000 whether you group by account, by
  month, by product or not at all, and the parts always sum to the whole.
- **Win rate is non-additive** because it is a ratio. You never sum it and never average it — you
  recompute it from the summed numerator and the summed denominator at whatever level you want. This is
  the same fact as [exercise 5.1](#51-a-ratio-of-sums-against-a-sum-of-ratios), seen from the
  aggregation side rather than the formula side.
- **Open pipeline as at a date is semi-additive**, and this is the one people get wrong. It is a
  *stock*, not a flow: the $250,000 open today is a complete snapshot of a position. Sum it across
  accounts and you get today's total pipeline, which is meaningful. Sum twelve monthly snapshots and you
  get a number twelve times too large that means nothing at all. Across time, take the period-end
  value — or the period average if that is the business definition, as it is for an average daily
  balance.
- **A distinct count is non-additive across dimensions.** The distinct accounts in the West plus the
  distinct accounts in the East happen to sum correctly here, because an account has one region — but
  distinct accounts in Q1 plus distinct accounts in Q2 do not sum to distinct accounts in the half, and
  never will, because accounts recur. Recompute distinct counts at the level you want to show them.

Declare additivity in the model rather than relying on memory. A measure that must not be summed should
ideally not be summable — expose it through a metric that aggregates it correctly, and the mistake
becomes unavailable. See [Going Deeper](going-deeper.md#additivity).

</details>

---

## Part 6 — Order of Operations & Context in the Viz Layer

[Read Part 6](../session-6-order-of-operations-and-context.md)

### 6.1 One field name, four defensible win rates

The opportunity fact contains: Closed Won $400,000 across 4 deals, Closed Lost $600,000 across 4 deals,
open $250,000 across 3 deals.

**Question.** Compute all four win rates that this single field name can legitimately produce. State
the spread, and say which question each one answers.

<details>
<summary>Answer</summary>

| Basis | Population | Calculation | Result |
|---|---|---|---|
| By value | Closed only | $400,000 / $1,000,000 | **40.0%** |
| By value | All opportunities | $400,000 / $1,250,000 | **32.0%** |
| By count | Closed only | 4 won / 8 closed | **50.0%** |
| By count | All opportunities | 4 won / 11 total | **36.4%** |

All four verified. The spread is **18 points**, from 32.0% to 50.0%.

Two independent choices produce four answers, and each answer is honest:

- **By value or by count** decides whether a $200,000 deal counts more than a $50,000 one. By value
  answers "what share of the money did we win"; by count answers "what share of the deals did we win".
- **Closed only or all opportunities** decides whether deals still in flight sit in the denominator.
  Closed-only answers "of the deals that reached a conclusion, how many went our way" — the
  execution question. All-opportunities answers "of everything we have worked, how much have we won so
  far" — which drags toward zero simply by having a healthy pipeline.

Eighteen points is more than enough to reverse a decision, and every one of these numbers can be
produced by a field called "win rate" without anybody doing anything wrong. That is why the resolution
is never "find the correct one". It is: pick a house definition, publish it as a governed metric with
its context baked in, and publish the alternatives as separately named metrics.

</details>

### 6.2 Where the filter lands decides the answer

Three configurations of the same view, all using a win-rate calculation defined as a ratio of sums by
value.

- **A.** No stage filter at all.
- **B.** `Stage IN (Closed Won, Closed Lost)` applied as a dimension filter.
- **C.** No stage filter, but a table calculation showing each stage's share of total value.

**Question.** Which win rate does A produce, and which does B? For C, do the shares sum to 100%, and
what changes if you promote a region filter to context?

<details>
<summary>Answer</summary>

**A produces 32.0%** — $400,000 of won value over $1,250,000 of all opportunity value. With no stage
filter, the three open opportunities are in the denominator.

**B produces 40.0%** — $400,000 over $1,000,000. The dimension filter ran *before* aggregation, at step
1 of the viz layer's order of operations, so it removed the open opportunities from the pool entirely.
The denominator was never $1,250,000; it was $1,000,000 from the start.

That is the whole mechanism. The calculation did not change. A filter entered at step 1 changes the
denominator of everything downstream; the same condition applied after aggregation would only change
which summarized rows survived. Dimension filters, context, aggregation, aggregate filters, then table
calculations — where a filter lands in that sequence decides the answer.

**C:** yes, the shares sum to 100% — Closed Won 32.0%, Closed Lost 48.0%, open 20.0% of $1,250,000. A
percent-of-total's denominator is the total of whatever is in context, and with nothing in context that
is the whole population.

Promote a region filter to context and every percentage recomputes against the West's $675,000 instead
of the company's $1,250,000. Same formula, same field, different denominator. And this is where the
32%-versus-40% argument really comes from: neither dashboard is broken, and nobody in the meeting can
see which step the filter entered at.

</details>

### 6.3 The percentages that add up to 54%

You build opportunity value by account, add a percent-of-total, and filter to the West region. Three
accounts have opportunities in the West: Acme Corp $350,000, Borealis Ltd $275,000, Fjord Logistics
$50,000.

**Question.** What percentages do you see with the region filter in context, and what do you see
without? Which is right?

<details>
<summary>Answer</summary>

**With region in context** — the denominator is the West's $675,000:

| Account | Value | Percent |
|---|---|---|
| Acme Corp | $350,000 | 51.9% |
| Borealis Ltd | $275,000 | 40.7% |
| Fjord Logistics | $50,000 | 7.4% |
| **Total** | **$675,000** | **100.0%** |

**Without it in context** — the numerators are the same West accounts, but the denominator is still the
company-wide $1,250,000:

| Account | Value | Percent |
|---|---|---|
| Acme Corp | $350,000 | 28.0% |
| Borealis Ltd | $275,000 | 22.0% |
| Fjord Logistics | $50,000 | 4.0% |
| **Total** | **$675,000** | **54.0%** |

**Both are right, and they answer different questions.** The first says "Acme is 52% of the West". The
second says "Acme is 28% of the company, and the West as a whole is 54% of it". The second is genuinely
useful — but only if the reader knows that is what they are looking at, and the column header will say
"% of total" either way.

The diagnostic is the column sum. **Percentages that do not add to 100 are telling you where the
denominator came from.** Under 100 means the denominator is larger than the displayed set, which is a
context question. Over 100 means the numerators are inflated, which is a fan-out question and a
different Part entirely.

If you want the company denominator explicitly rather than by accident, pin it with an LOD expression
instead of relying on a filter's placement — that way the intent is written down in the model where the
next person can read it.

</details>

### 6.4 Pin a measure to a grain the view is not using

You need a table at **order-line** grain — 11 rows — that also shows each account's total bookings on
every row, so you can compute each line's share of its account.

**Question.** What does `SUM([Order].[Amount])` return for Acme Corp in this view, and why? Write the
expression that returns the right number.

<details>
<summary>Answer</summary>

`SUM([Order].[Amount])` returns **$290,000** for Acme, against a truth of $200,000. Fan-out, one hop
lower than usual: `Order` to `Order Line` is one-to-many, and Acme's three orders have four lines
between them.

| Order | Amount | Lines | Contribution |
|---|---|---|---|
| R-001 | $60,000 | 1 | $60,000 |
| R-002 | $90,000 | 2 | $180,000 |
| R-003 | $50,000 | 1 | $50,000 |
| | **$200,000** | **4** | **$290,000** |

Across the whole dataset the same view reads $810,000 instead of $600,000, over 11 order lines.

The right expression pins the measure to the grain you mean, regardless of the grain the view is laid
out at:

```
{ FIXED [Account].[Account Name] : SUM([Order].[Amount]) }
```

This computes bookings **per account** and returns $200,000 on every one of Acme's four line rows —
which is exactly what a share-of-account denominator needs.

Two things to hold on to. First, this is the same idea as
[exercise 3.1](#31-the-100000-deal-that-reads-as-300000) — a measure at one grain displayed at another
— and the LOD expression is the tool for the cases where you cannot simply pick a better-grained
measure. Second, a `FIXED` expression is not filter-proof, and the way it is not matters: it **ignores**
an ordinary dimension filter, because it was computed before that filter was applied, but it
**respects** the same filter promoted to **context**. So the grain you fix and the filters you promote
together decide the number. State the grain, then decide the context — do not discover either of them
afterwards.

</details>

---

## Part 7 — Modeling for the Agent

[Read Part 7](../session-7-modeling-for-the-agent.md)

### 7.1 The YTD trap

The fiscal year starts on 1 February. Today is 25 August 2026. Bookings mean Closed Won opportunity
value, and the four won deals are: `O-006` $80,000 closing 16 January 2026, `O-004` $150,000 closing
20 May 2026, `O-005` $120,000 closing 12 June 2026, `O-007` $50,000 closing 8 July 2026.

**Question.** Compute calendar YTD and fiscal YTD bookings. What is the gap in currency and in
percentage terms, and which deal causes it? Bonus: what would fiscal YTD be if the fiscal year started
on 1 March instead, and what does that tell you about testing on one dataset?

<details>
<summary>Answer</summary>

**Calendar YTD** — 1 January to 25 August 2026: all four deals. $80,000 + $150,000 + $120,000 +
$50,000 = **$400,000** (verified).

**Fiscal YTD** — 1 February to 25 August 2026: `O-006` closed on 16 January, before the fiscal year
began, so it is excluded. $150,000 + $120,000 + $50,000 = **$320,000** (verified).

**The gap is $80,000, which is 20% of the number** (verified), and it is caused by exactly one deal:
`O-006` "Fjord Gadget Fleet". One January deal, one-fifth of the answer, and a question — "how are we
doing year to date?" — that gives no clue which one is wanted.

**Bonus: with a 1 March start, fiscal YTD is still $320,000.** No won deal closed in February, so
February's boundary and March's boundary produce the same answer. That is a warning about
verification, not a fact about fiscal calendars: **a test that passes on this dataset does not prove
your fiscal logic is right.** It proves it is right about January. Test the boundary deliberately —
first and last day of the fiscal year, and a deal in every month you can — rather than trusting a total
that happens to match.

The fix is structural. Materialize both flags in the date dimension, as `data/calendar.csv` does with
`is_calendar_ytd` and `is_fiscal_ytd`, so the two answers are two named columns instead of one
ambiguous phrase. Then declare which is the house default, out loud, in the metric's description.

</details>

### 7.2 Give the agent something to look up instead of guess

An agent is asked: "what did we sell last quarter?" The model exposes `[Opportunity].[Amount]`,
`[Opportunity Line Item].[Line Amount]`, `[Order].[Amount]` and `[Order Line].[Line Amount]`, all of
them numeric, all of them plausibly "what we sold", and none of them described.

**Question.** Which field is correct, and why are the other three wrong? Write a one-line description
for each so the agent stops guessing.

<details>
<summary>Answer</summary>

**`[Order].[Amount]` is correct.** "Sold" means an actual, completed sale, which is the `Order` fact.
An opportunity is a *forecast* — and $600,000 of orders against $1,250,000 of opportunity value means
the wrong choice is not a small error.

Why each of the others is wrong, and note that they are wrong in two different ways:

- `[Opportunity].[Amount]` — **wrong fact.** Pipeline, not sales. Includes losses and open deals.
- `[Opportunity Line Item].[Line Amount]` — **wrong fact and finer grain.** Same problem, plus it
  answers a product-level question that was not asked.
- `[Order Line].[Line Amount]` — **right fact, wrong grain.** It sums to the same $600,000, so it is
  not wrong in total — but it is the answer to "what did we sell, by product", and choosing it commits
  the agent to a grain the question never specified. That kind of near-miss is worse than an obvious
  error, because it survives a sanity check.

Descriptions that turn a guess into a lookup:

- `[Order].[Amount]` — "Total value of a completed order. Use this for bookings, revenue and 'what we
  sold'. One row per order."
- `[Order Line].[Line Amount]` — "Value of one product on one order. Use this for revenue by product.
  Sums to Order Amount."
- `[Opportunity].[Amount]` — "Forecast value of an opportunity, all stages including open and lost. Use
  this for pipeline, never for revenue. One row per opportunity."
- `[Opportunity Line Item].[Line Amount]` — "Forecast value of one product on one opportunity. Use this
  for pipeline by product. Sums to Opportunity Amount."

Two patterns are doing the work there. Each description says **what the row is** — that is the grain,
and it is what stops a grain mismatch. And each says **when to use it and when not to**, because
"never for revenue" is more useful to a guessing agent than any amount of accurate description.

Then go further: add synonyms so "bookings", "revenue" and "sales" all reach `Order.Amount`, and
publish a governed `Bookings_mtc` metric so the concept is answered from a definition rather than
improvised from a column. Descriptions are the highest-leverage metadata there is, and they are the
cheapest.

</details>

### 7.3 Diagnostic: standardization that has ossified

A team fixes their YTD problem thoroughly. They define one metric, `YTD_Bookings_mtc`, hardcoded to a
fiscal year starting 1 February, make it the only year-to-date metric in the model, and tune the agent
so that "year to date" maps to it. Then three things happen: the board asks for calendar-year numbers
for its deck, an acquired business unit turns out to run a fiscal year starting 1 July, and a regional
manager types "how are we doing so far this year?" and gets a poor answer.

**Question.** Name the three failures, and fix each without giving up the consistency they gained.

<details>
<summary>Answer</summary>

All three are **overfitting**: optimizing so hard for the common case that legitimate variation breaks.
Standardization removes ambiguity, which is good. Overfitting removes flexibility, which is not, and
the two are easy to confuse because they feel like the same virtue.

**Failure 1: a valid question became unaskable.** Calendar YTD is not a mistake — it is what a board
deck needs. Making the fiscal definition the *only* one available means the answer must now be produced
outside the model, in a spreadsheet nobody governs.

*Fix:* publish the alternative as a named, first-class metric, `Calendar_YTD_Bookings_mtc`, alongside
the fiscal one. Two explicit definitions is governance. One definition and a forbidden question is
brittleness.

**Failure 2: an organizational fact was hardcoded.** A fiscal calendar frozen to 1 February silently
gives the acquired unit wrong numbers — not an error, not a blank, just wrong, which is the worst of
the three outcomes.

*Fix:* parameterize where the organization genuinely varies. The fiscal calendar belongs in the date
dimension as data, resolvable per business unit, rather than as a constant in a metric definition. Note
the shape of the failure: the metric was right about the company it was written for and wrong about the
company it became.

**Failure 3: the vocabulary was too narrow.** "So far this year", "year to date" and "performance since
January" are the same question. Matching only one phrasing pushes the others onto a worse path.

*Fix:* synonyms, covering the phrasings people actually use. Cheap, and it costs nothing in
consistency — synonyms map varied language onto *one* definition, which is the opposite of ambiguity.

The pattern to keep: **sensible default, stated out loud in the description; valid alternatives as named
metrics; parameterized where the organization really varies; synonyms so natural phrasing still lands.**

</details>

### 7.4 Spot the convention errors

A colleague proposes five additions to the semantic data model.

1. `Win_Rate__clc` — a calculated field, `SUM([Opportunity].[Amount])` over won deals divided by the
   same over closed deals, left on the default aggregation type.
2. `Pipeline_Coverage_mtc` — a calculated field expression, not published as a metric.
3. `Bookings_clc = SUM([Amount])`.
4. `Margin_clc = [Order Line].[Line Amount] - [Line_Cost_clc]`.
5. `Bookings_West_clc = SUM([Order].[Amount])` filtered to `[Account].[Region] = West`, to be used as
   the West team's bookings figure.

**Question.** Find every problem.

<details>
<summary>Answer</summary>

**1. Two problems.** The double underscore in `Win_Rate__clc` is invalid — the suffix is `_clc`, with a
single underscore. And the expression already contains `SUM`, so the aggregation type must be
`UserAgg`; on the default it will be re-aggregated and the result will be wrong. Correct:
`Win_Rate_clc`, aggregation type `UserAgg`.

**2. Suffix does not match the artefact.** `_mtc` is for semantic metrics; `_clc` is for calculated
fields. A calculated field named `Pipeline_Coverage_mtc` will mislead every reader and every agent that
uses the naming convention as a signal. Either rename it `Pipeline_Coverage_clc` or — better, since
pipeline coverage is a reused KPI — publish it properly as a metric and let the name be true.

**3. Unqualified table field.** Table fields are always qualified as `[TableName].[FieldName]`, so this
must be `SUM([Order].[Amount])`. `[Amount]` on its own is ambiguous in a model that has an amount on
`Opportunity` as well as on `Order`, which is exactly the ambiguity
[exercise 7.2](#72-give-the-agent-something-to-look-up-instead-of-guess) is about. Being unqualified
also makes it look like a reference to a calculated field, which it is not.

**4. Correct.** The table field is qualified, `[Order Line].[Line Amount]`; the calculated field is
model-level and therefore referenced unqualified, `[Line_Cost_clc]`; the suffix is right; and the
expression contains no aggregation, so it is a row-level calculation and does not need `UserAgg`. Worth
asking, though, whether a row-level margin on the finest-grained object in the model should be a
query-time calculation at all — that is
[exercise 5.3](#53-diagnostic-place-four-calculations-then-find-the-cost-bomb).

**5. Conventions fine, design wrong.** The naming and qualification are correct, but baking a region
filter into a field name creates a metric per region — and then per segment, and per product family.
That is not a calculated field; it is a *filtered view* of one, and it should be
`SUM([Order].[Amount])` with region supplied as a filter or as context. Encode the dimension in the
model, not in the metric name, or you will maintain a combinatorial explosion of near-identical
definitions that inevitably drift apart.

</details>
