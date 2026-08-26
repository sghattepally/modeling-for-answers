# The dataset

*Eleven opportunities and nine orders, tuned so every number in the series lands on a clean
figure you can check by hand.*

Back to [series overview](../README.md)

---

## Run it

```bash
python3 build_dataset.py    # regenerates all eight CSVs
python3 verify_numbers.py   # asserts every figure the articles quote
```

No dependencies beyond the Python standard library. `verify_numbers.py` exits non-zero if any
assertion fails, so it works as a pre-publish check.

## Why it's this small

Small enough to verify by hand, large enough to break in every way the series describes. A reader
who doubts a claim can open a CSV, count on their fingers, and settle it. That matters more than
realism here — a 100,000-row dataset would make every figure unverifiable and every lesson a
matter of trust.

## The files

| File | Grain | Rows |
|---|---|---|
| `accounts.csv` | one row per account | 10 |
| `users.csv` | one row per user | 4 |
| `products.csv` | one row per product | 6 |
| `calendar.csv` | one row per day | 488 |
| `opportunities.csv` | one row per opportunity | 11 |
| `opportunity_line_items.csv` | one row per product per opportunity | 16 |
| `orders.csv` | one row per order | 9 |
| `order_lines.csv` | one row per product per order | 11 |

Two facts (`opportunities`, `orders`), two bridges (`opportunity_line_items`, `order_lines`), and
four conformed dimensions. `calendar.csv` is generated rather than hand-written, and carries both
calendar and fiscal attributes with a fiscal year starting 1 February.

## What each figure is tuned for

The data is not random. Each row exists to make a specific failure reproducible.

| Teaching moment | How the data delivers it | Part |
|---|---|---|
| Fan-out | `O-001` is $100,000 with exactly 3 line items → naive sum reads $300,000 | 3 |
| Allocation | those 3 lines are $40k/$35k/$25k → factors 0.40/0.35/0.25 summing to 1.00 | 4 |
| Chasm trap | opportunities concentrated on accounts that also have orders → bookings inflate 2.08×, opportunity value 1.72× | 3 |
| Silent deletion | `A-007` has orders and no opportunities; `A-003` the reverse → an inner join drops both | 3, 4 |
| Four win rates | won $400k, closed $1,000k, all $1,250k, 4 won of 8 closed of 11 → 40% / 32% / 50% / 36.4% | 5, 6 |
| Whitespace | 4 accounts bought with nothing open ($300k); 1 net-new logo ($75k); 3 with no facts at all | 4 |
| Product whitespace | Gadget and Gizmo sell but aren't forecast ($235k); Training Credits is forecast but never sells | 4 |
| YTD trap | fiscal year starts 1 February and `R-006` is a $120,000 order placed 20 January | 1, 7 |
| No-op filter | 4 West accounts, 3 with opportunities → $675,000, against $1,250,000 unfiltered | 2 |

If you change the data, `verify_numbers.py` will tell you which article now needs updating. That
is the point of it.

## Conventions

- **"Bookings" always means orders.** Opportunities are pipeline; Orders are actuals. The series
  argues that a term with two meanings is a governance failure, so it doesn't commit one.
- **Open stages** are Discovery, Proposal and Negotiation. Closed stages are Closed Won and
  Closed Lost.
- **The "as of" date is 25 August 2026.** All year-to-date figures are relative to it, and it's
  set in one place at the top of both scripts.
- **Fiscal years are named for the year they end in**, so 1 Feb 2026 – 31 Jan 2027 is FY2027.

## Using it with SQL

The CSVs load into anything. For a quick local check with DuckDB:

```sql
CREATE TABLE opportunities AS SELECT * FROM read_csv_auto('opportunities.csv');
CREATE TABLE orders        AS SELECT * FROM read_csv_auto('orders.csv');
CREATE TABLE accounts      AS SELECT * FROM read_csv_auto('accounts.csv');

-- The chasm trap, reproduced. Returns 1,245,000 instead of 600,000.
SELECT SUM(r.amount) AS inflated_bookings
FROM orders r
JOIN opportunities o ON o.account_id = r.account_id;

-- The correct pattern: aggregate each fact first, then FULL OUTER JOIN.
WITH pipeline AS (
  SELECT account_id, SUM(amount) AS open_pipeline
  FROM opportunities
  WHERE stage NOT IN ('Closed Won', 'Closed Lost')
  GROUP BY account_id
),
bookings AS (
  SELECT account_id, SUM(amount) AS bookings
  FROM orders
  GROUP BY account_id
)
SELECT COALESCE(p.account_id, b.account_id) AS account_id,
       p.open_pipeline,
       b.bookings
FROM pipeline p
FULL OUTER JOIN bookings b ON p.account_id = b.account_id
ORDER BY 1;
```

The second query returns 7 rows, including the whitespace ones — `A-003` Cyan Systems with
pipeline and no bookings, and `A-004` through `A-007` with bookings and no pipeline. Change
`FULL OUTER` to `INNER` and you get 2 rows. That one-word edit is the entire argument of Part 4.

One subtlety worth noticing: those 7 rows are not all 10 accounts. `A-008`, `A-009` and `A-010`
have neither opportunities nor orders, so they appear in neither summary and a full outer join
between the two cannot invent them. To get all ten — the "no relationship yet" cell of the
whitespace matrix — you have to start from the Account dimension and left-join both summaries
onto it:

```sql
SELECT a.account_id, a.account_name, p.open_pipeline, b.bookings
FROM accounts a
LEFT JOIN pipeline p ON p.account_id = a.account_id
LEFT JOIN bookings b ON b.account_id = a.account_id
ORDER BY 1;
```

Which is a small illustration of a larger point: a full outer join preserves everything **the
two facts know about**. Dimension members that no fact references are a different question, and
they need the dimension to be the driving table.
