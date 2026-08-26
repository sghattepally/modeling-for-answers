# Agent Eval Set
*A golden question set for the Sales Pipeline & Bookings model. Ask these, check the numbers, fix what fails.*

Back to [series overview](../README.md) · Referenced from
[Part 7 — Modeling for the Agent](../session-7-modeling-for-the-agent.md)

---

## Why this exists

You cannot tell whether your metadata is good by reading it. You find out by asking the agent
questions whose answers you already know.

Every expected value below is asserted by [`../data/verify_numbers.py`](../data/verify_numbers.py).
Run that first; it is the source of truth, and if it passes then any disagreement is the agent's,
not the data's.

**How to score:** assert the number. A confidently-worded wrong answer is a failure, and a
correct number with a vague explanation is a pass. You are testing whether the model is
answerable, not whether the prose is nice.

**When to run:** after any change to the model, the metadata, the underlying data, or the
platform. The value of a regression suite is almost entirely in being run again.

---

## Tier 1 — Can it find the right measure at all?

These test the basics from Parts 1 and 2: is the fact unambiguous, is the measure obvious, does
the stage filter apply.

| # | Ask exactly this | Expected | Fails if | Go back to |
|---|---|---|---|---|
| 1 | What's my open pipeline? | **$250,000** | Returns $1,250,000 (no stage filter) or $400,000 (used won instead of open) | Part 1 — descriptions; Part 6 — baked-in context |
| 2 | How much have we sold? | **$600,000** | Returns opportunity value instead of order value | Part 7 — "bookings means Order" in the description |
| 3 | Show me pipeline by rep | **Ana Ruiz $175,000, Ben Okafor $75,000** | Doesn't map "rep" to `User`, or returns all four users | Part 7 — synonyms |
| 4 | Pipeline for Acme | **$100,000** | Returns $350,000 (all stages, not just open) | Part 6 — context |

Question 3 is quietly a good test: only two of the four users hold open pipeline, so an agent
that lists all four with zeros has probably joined the wrong way round.

---

## Tier 2 — Does it respect grain?

These are the Part 3 traps. Each one has a specific wrong answer that a naive query produces,
which is what makes them diagnostic rather than decorative.

| # | Ask exactly this | Expected | The wrong answer to watch for | Go back to |
|---|---|---|---|---|
| 5 | What's the amount for the Acme Platform Expansion deal? | **$100,000** | **$300,000** — fan-out, the header amount summed across three line items | Part 3 |
| 6 | Revenue by product | totals to **$600,000** | Anything larger — all-or-nothing attribution instead of an allocation factor | Part 4 |
| 7 | Show me pipeline and bookings by account | bookings **$600,000**, pipeline **$1,250,000** | bookings $1,245,000 and pipeline $2,150,000 — the chasm trap | Part 3 / Part 4 |
| 8 | Which products sell but aren't in our pipeline? | **Gadget and Gizmo, $235,000** | Empty result, or products that are in pipeline | Part 4 — conformed Product dimension |

Question 7 is the highest-value question in the set. Two facts, one shared dimension, and the
signature of failure is that **both** numbers are wrong by **different** multiples — 2.08× and
1.72×. If you only check one measure you may conclude the model is merely a bit off.

---

## Tier 3 — Does it use your definitions or invent its own?

Parts 5 and 6. There is more than one defensible answer here, and the test is whether the agent
applies the one you declared.

| # | Ask exactly this | Expected | Fails if | Go back to |
|---|---|---|---|---|
| 9 | What's our win rate? | **40.0%** (house default: by value, closed only) | Returns 32.0%, 50.0% or 36.4% — all correct answers to questions you didn't ask | Part 5 / Part 6 |
| 10 | What's our win rate by count? | **50.0%** | Returns 40.0% — didn't distinguish the two named metrics | Part 5 |
| 11 | How many deals did we win? | **4** | Returns $400,000 — confused count basis with value basis | Part 5 |
| 12 | What share of all our pipeline have we won? | **32.0%** | Returns 40.0% — didn't widen the denominator when the question asked for it | Part 6 |

Questions 9 and 12 are the pair that matters. The agent must return **different** numbers,
because they are different questions — and it must not return 32.0% for question 9.

---

## Tier 4 — Does it know your conventions?

Part 7. These have no correct answer derivable from the data alone; they are only answerable
if you wrote the convention down.

| # | Ask exactly this | Expected | Fails if | Go back to |
|---|---|---|---|---|
| 13 | How are we doing this year? | **$480,000** (fiscal YTD, the house default) | Returns $600,000 — used the calendar year | Part 7 — business preferences |
| 14 | Bookings since January | **$600,000** (calendar) | Returns $480,000, or can't answer at all | Part 7 — overfitting |
| 15 | What was pipeline generated this quarter? | uses **Created Date**, not Close Date | Uses Close Date — didn't respect the role | Part 2 — role-playing dimensions |
| 16 | Bookings for Granite Bank | **$55,000** | Returns zero or "no data" — the account exists in only one fact | Part 4 — full outer join |

Question 13 is the flagship. There is a **$120,000, 20%** gap between the two readings, caused
entirely by Delta Foods' order on 20 January. A good answer states which calendar it used and
offers the other; a bad answer just picks.

Question 14 is the overfitting check. An organization that hardcoded fiscal YTD as the only
option will fail this one, and the failure is worse than a wrong number — the question becomes
unaskable.

Question 16 is the quiet one. Granite Bank has orders and no opportunities. If your stitch is an
inner join it vanishes, and the agent will tell you there's no data — confidently, and wrongly.

---

## Tier 5 — Does it degrade honestly?

The most underrated category. An agent that says "I can't tell" is more valuable than one that
guesses, and these questions have no single right answer on purpose.

| # | Ask exactly this | A good answer | A bad answer |
|---|---|---|---|
| 17 | What's our best account? | Asks what "best" means, or states the measure it chose | Silently picks one of bookings, pipeline, or count |
| 18 | How's Helios Energy doing? | Reports that Helios has no opportunities and no orders | Returns $0 with no explanation, implying decline rather than absence |
| 19 | What's our conversion rate? | Notes this isn't a governed metric, or maps it to win rate and says so | Invents a fresh ratio and presents it as authoritative |
| 20 | Are we going to hit our number? | Declines — there's no quota or target in this model | Fabricates a target |

Question 18 distinguishes "zero" from "no data," which is the same distinction the Unknown-member
pattern exists to make visible (Part 2).

---

## Scoring sheet

| Tier | What it proves | Questions | Pass bar |
|------|----------------|-----------|----------|
| 1 | The model is navigable | 1–4 | 4 / 4 |
| 2 | Grain is respected | 5–8 | 4 / 4 |
| 3 | Your definitions win | 9–12 | 4 / 4 |
| 4 | Your conventions are stated | 13–16 | 4 / 4 |
| 5 | It degrades honestly | 17–20 | 3 / 4 |

Tiers 1 through 4 should be **100%**. Every one of those failures is a structural problem with a
specific fix in a specific part of the series — not a prompt-engineering problem, and not
something to tune around.

When a question fails, work through the causes in this order:

1. **The model is wrong** → Parts 1–4. Shape, cardinality, grain, conformance, join type.
2. **The metric isn't governed** → Part 5. The agent improvised because you gave it nothing to look up.
3. **The context isn't baked in** → Part 6. The definition exists but its denominator is left to the caller.
4. **The metadata is missing** → Part 7. It's correct and findable but not described.

Note what is not on that list: "the agent is bad." In our experience it almost never is.

---

## Adding your own

Two rules that keep an eval set useful as it grows:

- **Every trap gets a question.** If you hit a modeling bug in production, write the question
  that would have caught it before you fix the bug. That's how the set earns its keep.
- **Keep the ambiguous ones.** Questions with more than one defensible answer are the most
  valuable in the file, because they test your *defaults* rather than your data. Delete them and
  you're only testing arithmetic.
