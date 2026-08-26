#!/usr/bin/env python3
"""
Verifies every number quoted in the "Modeling for Answers" series against the CSVs.

This is the file that keeps the series honest. If you change the dataset, run this;
if an assertion fails, either the data moved or an article needs updating. The output
doubles as the appendix of worked figures.

Run:  python3 verify_numbers.py
"""

import csv
import os
from collections import defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
AS_OF = date(2026, 8, 25)
FISCAL_START_MONTH = 2

OPEN_STAGES = {"Discovery", "Proposal", "Negotiation"}
WON_STAGES = {"Closed Won"}
LOST_STAGES = {"Closed Lost"}
CLOSED_STAGES = WON_STAGES | LOST_STAGES

failures = []
checks = 0


def load(name):
    with open(os.path.join(HERE, name)) as fh:
        return list(csv.DictReader(fh))


def money(n):
    return f"${n:,.0f}"


def check(label, actual, expected, fmt=money):
    """Assert a figure and print it in a form that can be pasted into an article."""
    global checks
    checks += 1
    ok = actual == expected
    if not ok:
        failures.append(f"{label}: expected {expected}, got {actual}")
    mark = "ok  " if ok else "FAIL"
    shown = fmt(actual) if fmt else str(actual)
    print(f"  [{mark}] {label:58s} {shown}")


def pct(n):
    return f"{n * 100:.1f}%"


def plain(n):
    return str(n)


def parse_date(s):
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def fiscal_year(d):
    return d.year + 1 if d.month >= FISCAL_START_MONTH else d.year


# ---------------------------------------------------------------------------

accounts = load("accounts.csv")
products = load("products.csv")
opps = load("opportunities.csv")
opp_lines = load("opportunity_line_items.csv")
orders = load("orders.csv")
order_lines = load("order_lines.csv")

for row in opps:
    row["amount"] = int(row["amount"])
for row in orders:
    row["amount"] = int(row["amount"])
for row in opp_lines:
    row["line_amount"] = int(row["line_amount"])
for row in order_lines:
    row["line_amount"] = int(row["line_amount"])

print("\n" + "=" * 86)
print("PART 3 — Grain")
print("=" * 86)

check("Opportunities: one row per opportunity", len(opps), 11, plain)
check("Opportunity line items: one row per product per opportunity", len(opp_lines), 16, plain)
check("Orders: one row per order", len(orders), 9, plain)
check("Order lines: one row per product per order", len(order_lines), 11, plain)

print("\n" + "=" * 86)
print("PART 2 — The silent no-op filter (Region = West)")
print("=" * 86)

region_of = {a["account_id"]: a["region"] for a in accounts}
all_opp_value = sum(o["amount"] for o in opps)
west_value = sum(o["amount"] for o in opps if region_of[o["account_id"]] == "West")
west_accounts = sorted(a["account_name"] for a in accounts if a["region"] == "West")
west_with_opps = sorted({
    next(a["account_name"] for a in accounts if a["account_id"] == o["account_id"])
    for o in opps if region_of[o["account_id"]] == "West"})

check("Accounts in the West region", len(west_accounts), 4, plain)
check("  of which have at least one opportunity", west_with_opps,
      ["Acme Corp", "Borealis Ltd", "Fjord Logistics"], plain)
# The no-op: the filter is declared but the query never reaches Account, so the
# unfiltered total is what appears on screen.
check("Total with the Region filter no-opping", all_opp_value, 1250000)
check("Total once the query is forced to visit Account", west_value, 675000)

print("\n" + "=" * 86)
print("PART 3 — Fan-out (the $100,000 deal that reads as $300,000)")
print("=" * 86)

o1 = next(o for o in opps if o["opportunity_id"] == "O-001")
o1_lines = [l for l in opp_lines if l["opportunity_id"] == "O-001"]

check("O-001 header amount (the truth)", o1["amount"], 100000)
check("O-001 line item count", len(o1_lines), 3, plain)
check("O-001 line amounts sum to the header", sum(l["line_amount"] for l in o1_lines), 100000)
# Fan-out is the header amount repeated once per child row, then summed.
check("Naive SUM(Opportunity.Amount) across line items", o1["amount"] * len(o1_lines), 300000)
check("Inflation factor", len(o1_lines), 3, lambda n: f"{n}x")

print("\n" + "=" * 86)
print("PART 4 — Allocation: how to split $100,000 across three products")
print("=" * 86)

equal = o1["amount"] / len(o1_lines)
check("Equal split, per product (simple, usually wrong)", round(equal, 2), 33333.33,
      lambda n: f"${n:,.2f}")
for line in o1_lines:
    name = next(p["product_name"] for p in products if p["product_id"] == line["product_id"])
    factor = line["line_amount"] / o1["amount"]
    print(f"         by line amount: {name:18s} {money(line['line_amount']):>10s}  "
          f"(allocation factor {factor:.2f})")
check("By-line allocation factors sum to 1.00",
      round(sum(l["line_amount"] / o1["amount"] for l in o1_lines), 4), 1.0,
      lambda n: f"{n:.2f}")
check("All-or-nothing attribution (triple counts)", o1["amount"] * len(o1_lines), 300000)

print("\n" + "=" * 86)
print("PART 6 — One field name, four defensible win rates")
print("=" * 86)

won_val = sum(o["amount"] for o in opps if o["stage"] in WON_STAGES)
lost_val = sum(o["amount"] for o in opps if o["stage"] in LOST_STAGES)
open_val = sum(o["amount"] for o in opps if o["stage"] in OPEN_STAGES)
closed_val = won_val + lost_val
all_val = closed_val + open_val

won_ct = sum(1 for o in opps if o["stage"] in WON_STAGES)
closed_ct = sum(1 for o in opps if o["stage"] in CLOSED_STAGES)
all_ct = len(opps)

check("Closed Won value", won_val, 400000)
check("Closed Lost value", lost_val, 600000)
check("Closed total value", closed_val, 1000000)
check("Open pipeline value", open_val, 250000)
check("All opportunity value", all_val, 1250000)

check("Win Rate by Value, closed only", round(won_val / closed_val, 4), 0.4, pct)
check("Win Rate by Value, all opportunities", round(won_val / all_val, 4), 0.32, pct)
check("Win Rate by Count, closed only", round(won_ct / closed_ct, 4), 0.5, pct)
check("Win Rate by Count, all opportunities", round(won_ct / all_ct, 4), 0.3636, pct)

print("\n" + "=" * 86)
print("PART 3 — The chasm trap: two facts, one shared dimension, no shared grain")
print("=" * 86)

opps_by_acct = defaultdict(list)
for o in opps:
    opps_by_acct[o["account_id"]].append(o)
orders_by_acct = defaultdict(list)
for r in orders:
    orders_by_acct[r["account_id"]].append(r)

true_bookings = sum(r["amount"] for r in orders)
true_pipeline_all = sum(o["amount"] for o in opps)

# A naive join through Account pairs every order with every opportunity for that
# account -- a partial Cartesian product. Accounts missing from either fact drop out.
shared = [a["account_id"] for a in accounts
          if opps_by_acct[a["account_id"]] and orders_by_acct[a["account_id"]]]
inflated_bookings = sum(
    sum(r["amount"] for r in orders_by_acct[a]) * len(opps_by_acct[a]) for a in shared)
inflated_pipeline = sum(
    sum(o["amount"] for o in opps_by_acct[a]) * len(orders_by_acct[a]) for a in shared)
paired_rows = sum(len(orders_by_acct[a]) * len(opps_by_acct[a]) for a in shared)

check("True bookings (Orders alone)", true_bookings, 600000)
check("Bookings after the naive join", inflated_bookings, 1245000)
check("Bookings inflation factor", round(inflated_bookings / true_bookings, 3), 2.075,
      lambda n: f"{n:.2f}x")
check("True opportunity value (Opportunities alone)", true_pipeline_all, 1250000)
check("Opportunity value after the naive join", inflated_pipeline, 2150000)
check("Opportunity inflation factor", round(inflated_pipeline / true_pipeline_all, 3), 1.72,
      lambda n: f"{n:.2f}x")
check("Rows produced by the partial Cartesian product", paired_rows, 18, plain)

# The join does not only inflate. It silently discards accounts present in one fact only.
dropped_orders = [a["account_id"] for a in accounts
                  if orders_by_acct[a["account_id"]] and not opps_by_acct[a["account_id"]]]
dropped_opps = [a["account_id"] for a in accounts
                if opps_by_acct[a["account_id"]] and not orders_by_acct[a["account_id"]]]
check("Accounts with orders silently dropped", dropped_orders, ["A-007"], plain)
check("Accounts with opportunities silently dropped", dropped_opps, ["A-003"], plain)
check("Booking value lost to the drop",
      sum(r["amount"] for r in orders_by_acct["A-007"]), 55000)

# The correct pattern: aggregate each fact at its own grain, then FULL OUTER JOIN.
print("\n  Drill-across (aggregate first, then align on the conformed key):")
agg_pipeline = {a: sum(o["amount"] for o in v if o["stage"] in OPEN_STAGES)
                for a, v in opps_by_acct.items()}
agg_bookings = {a: sum(r["amount"] for r in v) for a, v in orders_by_acct.items()}
check("Drill-across bookings total (matches source)",
      sum(agg_bookings.values()), 600000)
check("Drill-across open pipeline total (matches source)",
      sum(agg_pipeline.values()), 250000)

print("\n" + "=" * 86)
print("PART 4 — Whitespace: set differences between two conformed facts")
print("=" * 86)

has_orders = {a for a in orders_by_acct if orders_by_acct[a]}
has_open = {a for a, v in opps_by_acct.items()
            if any(o["stage"] in OPEN_STAGES for o in v)}
all_accts = {a["account_id"] for a in accounts}

at_risk = sorted(has_orders - has_open)
net_new = sorted(has_open - has_orders)
both = sorted(has_orders & has_open)
neither = sorted(all_accts - has_orders - has_open)

check("Bought before, nothing open (re-engagement list)", at_risk,
      ["A-004", "A-005", "A-006", "A-007"], plain)
check("  their past booking value", sum(agg_bookings[a] for a in at_risk), 300000)
check("Open pipeline, no order history (net-new logos)", net_new, ["A-003"], plain)
check("  their open pipeline value", sum(agg_pipeline[a] for a in net_new), 75000)
check("Both (existing customers with pipeline)", both, ["A-001", "A-002"], plain)
check("  their open pipeline value", sum(agg_pipeline[a] for a in both), 175000)
# Bookings happen to split exactly in half between the two cells. Worth asserting so a
# reader does not mistake the repeated $300,000 for a copy-paste error.
check("  their past booking value (also $300k \u2014 a coincidence)",
      sum(agg_bookings[a] for a in both), 300000)
check("Neither (prospects, no facts at all)", neither,
      ["A-008", "A-009", "A-010"], plain)
check("Accounts recovered only by a FULL OUTER JOIN", len(at_risk) + len(net_new), 5, plain)

# Product-level whitespace.
open_opp_ids = {o["opportunity_id"] for o in opps if o["stage"] in OPEN_STAGES}
products_forecast = {l["product_id"] for l in opp_lines
                     if l["opportunity_id"] in open_opp_ids}
sold_value = defaultdict(int)
for l in order_lines:
    sold_value[l["product_id"]] += l["line_amount"]
products_sold = set(sold_value)

sold_not_forecast = sorted(products_sold - products_forecast)
forecast_not_sold = sorted(products_forecast - products_sold)

check("Products sold but absent from open pipeline", sold_not_forecast,
      ["P-002", "P-003"], plain)
check("  demand the pipeline is blind to",
      sum(sold_value[p] for p in sold_not_forecast), 235000)
check("Products in open pipeline that have never sold", forecast_not_sold,
      ["P-006"], plain)

print("\n" + "=" * 86)
print("PART 7 — The YTD trap (fiscal year starts February 1)")
print("=" * 86)

# "Bookings" means Orders throughout the series -- Opportunities are pipeline, Orders are
# actuals. Keeping that consistent matters: the series' own argument is that a term with
# two meanings is a governance failure.
cal_ytd = sum(r["amount"] for r in orders
              if parse_date(r["order_date"]).year == AS_OF.year
              and parse_date(r["order_date"]) <= AS_OF)
fis_ytd = sum(r["amount"] for r in orders
              if fiscal_year(parse_date(r["order_date"])) == fiscal_year(AS_OF)
              and parse_date(r["order_date"]) <= AS_OF)

check("Calendar YTD bookings (Jan 1 - Aug 25, 2026)", cal_ytd, 600000)
check("Fiscal YTD bookings (Feb 1 - Aug 25, 2026)", fis_ytd, 480000)
check("Gap between the two answers", cal_ytd - fis_ytd, 120000)
check("Relative gap", round((cal_ytd - fis_ytd) / cal_ytd, 4), 0.2, pct)
january = [r["order_id"] for r in orders
           if parse_date(r["order_date"]).month == 1
           and parse_date(r["order_date"]).year == 2026]
check("The single order responsible", january, ["R-006"], plain)
check("  and the account it belongs to",
      [r["account_id"] for r in orders if r["order_id"] == "R-006"], ["A-004"], plain)

print("\n" + "=" * 86)
print("REFERENCE LAYER — figures quoted in reference/ and Semantic Models/")
print("=" * 86)

# Fan-out across every opportunity, not just O-001 (exercises.md).
lines_per_opp = defaultdict(int)
for line in opp_lines:
    lines_per_opp[line["opportunity_id"]] += 1
fanned = sum(o["amount"] * lines_per_opp[o["opportunity_id"]] for o in opps)
check("Fan-out across all opportunities", fanned, 1775000)
check("  inflation factor", round(fanned / all_val, 4), 1.42, lambda n: f"{n:.2f}x")
check("Opportunity line amounts reconcile to headers",
      sum(l["line_amount"] for l in opp_lines), 1250000)

# The same fan-out on the orders side of the model (exercises.md).
lines_per_order = defaultdict(int)
for line in order_lines:
    lines_per_order[line["order_id"]] += 1
fanned_orders = sum(r["amount"] * lines_per_order[r["order_id"]] for r in orders)
check("Fan-out across all orders", fanned_orders, 810000)
check("  inflation factor", round(fanned_orders / 600000, 4), 1.35,
      lambda n: f"{n:.2f}x")
check("Order line amounts reconcile to headers",
      sum(l["line_amount"] for l in order_lines), 600000)

# Bookings by region, and the percent-of-total split those imply (exercises.md).
bookings_by_region = defaultdict(int)
for r in orders:
    bookings_by_region[region_of[r["account_id"]]] += r["amount"]
check("Bookings, West", bookings_by_region["West"], 345000)
check("Bookings, East", bookings_by_region["East"], 175000)
check("Bookings, Central", bookings_by_region["Central"], 80000)
check("  and they total", sum(bookings_by_region.values()), 600000)
for reg, expected in (("West", 0.575), ("East", 0.2917), ("Central", 0.1333)):
    check(f"  {reg} as percent of total",
          round(bookings_by_region[reg] / 600000, 4), expected, pct)

# Opportunity value by region (exercises.md).
by_region = defaultdict(int)
for o in opps:
    by_region[region_of[o["account_id"]]] += o["amount"]
check("Opportunity value, West", by_region["West"], 675000)
check("Opportunity value, East", by_region["East"], 370000)
check("Opportunity value, Central", by_region["Central"], 205000)
check("  and they total", sum(by_region.values()), 1250000)

# Averaging per-owner ratios is not the company ratio (going-deeper.md).
owner_rates = []
for uid in {o["owner_user_id"] for o in opps}:
    mine = [o for o in opps if o["owner_user_id"] == uid]
    closed = sum(o["amount"] for o in mine if o["stage"] in CLOSED_STAGES)
    if closed:
        w = sum(o["amount"] for o in mine if o["stage"] in WON_STAGES)
        owner_rates.append(w / closed)
check("Mean of per-owner win rates (wrong)",
      round(sum(owner_rates) / len(owner_rates), 3), 0.396, pct)
check("Company win rate by value (right)", round(won_val / closed_val, 3), 0.4, pct)

# Role-playing dimensions: "last year" depends entirely on which date you mean.
created_2025 = [o for o in opps if parse_date(o["created_date"]).year == 2025]
closed_2025 = [o for o in opps if parse_date(o["close_date"]).year == 2025]
check("Opportunities created in 2025", len(created_2025), 2, plain)
check("  their value", sum(o["amount"] for o in created_2025), 180000)
check("Opportunities closed in 2025", len(closed_2025), 0, plain)

# Type 2 vs Type 1 on Acme's region change, effective 1 June 2026 (exercises.md).
acme = orders_by_acct["A-001"]
check("Acme bookings before 1 Jun 2026 (the 'West' period)",
      sum(r["amount"] for r in acme if parse_date(r["order_date"]) < date(2026, 6, 1)),
      150000)
check("Acme bookings from 1 Jun 2026 (the 'East' period)",
      sum(r["amount"] for r in acme if parse_date(r["order_date"]) >= date(2026, 6, 1)),
      50000)

# The opportunity-side YTD split, kept distinct from bookings on purpose.
won = [o for o in opps if o["stage"] in WON_STAGES]
check("Closed-won value, calendar YTD (not 'bookings')",
      sum(o["amount"] for o in won
          if parse_date(o["close_date"]).year == AS_OF.year
          and parse_date(o["close_date"]) <= AS_OF), 400000)
check("Closed-won value, fiscal YTD (not 'bookings')",
      sum(o["amount"] for o in won
          if fiscal_year(parse_date(o["close_date"])) == fiscal_year(AS_OF)
          and parse_date(o["close_date"]) <= AS_OF), 320000)

print("\n" + "=" * 86)
print("PART 7 — Expected answers for the agent eval set")
print("=" * 86)

users = load("users.csv")
name_of_user = {u["user_id"]: u["user_name"] for u in users}
open_opps = [o for o in opps if o["stage"] in OPEN_STAGES]

by_owner = defaultdict(int)
for o in open_opps:
    by_owner[name_of_user[o["owner_user_id"]]] += o["amount"]

check("Q1  open pipeline", sum(o["amount"] for o in open_opps), 250000)
check("Q2  bookings this year, fiscal default", fis_ytd, 480000)
check("Q3  win rate, house default", round(won_val / closed_val, 4), 0.4, pct)
check("Q4  deals won", won_ct, 4, plain)
check("Q5  open pipeline for Acme Corp", agg_pipeline["A-001"], 100000)
check("Q6  revenue by product, total", sum(sold_value.values()), 600000)
check("Q7  accounts that bought with nothing open", len(at_risk), 4, plain)
check("Q7  their value", sum(agg_bookings[a] for a in at_risk), 300000)
check("Q8  distinct owners holding open pipeline", sorted(by_owner), 
      ["Ana Ruiz", "Ben Okafor"], plain)
check("Q8  Ana Ruiz open pipeline", by_owner["Ana Ruiz"], 175000)
check("Q8  Ben Okafor open pipeline", by_owner["Ben Okafor"], 75000)
check("Q9  bookings for Granite Bank", agg_bookings["A-007"], 55000)
check("Q10 amount for the Acme platform deal", o1["amount"], 100000)

print("\n" + "=" * 86)
if failures:
    print(f"{len(failures)} of {checks} checks FAILED:\n")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
print(f"All {checks} checks passed. Every figure in the series is derived from the CSVs.")
print("=" * 86 + "\n")
