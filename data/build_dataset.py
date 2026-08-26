#!/usr/bin/env python3
"""
Builds the reproducible micro-dataset used throughout the "Modeling for Answers" series.

Every number quoted in the articles is derived from these tables. The dataset is
deliberately tiny (11 opportunities, 9 orders) so a reader can verify any figure by hand,
but it is tuned so that each teaching moment lands on a clean, memorable number:

  - Fan-out:        Opportunity O-001 is $100,000 with exactly 3 line items -> naive
                    SUM(Opportunity.Amount) across line items reads $300,000.
  - Chasm trap:     Joining Orders and Opportunities through Account inflates bookings
                    from $600,000 to $1,245,000 (2.08x) and silently drops one account.
  - Win rate:       Four defensible answers from one field name (40% / 32% / 50% / 36.4%).
  - YTD trap:       Fiscal year starts Feb 1, so fiscal YTD and calendar YTD differ by
                    exactly one January deal ($80,000).
  - Whitespace:     Four accounts bought before but have nothing open; one is a net-new
                    logo; two products sell but are never forecast; one is forecast but
                    never sells.

Run:  python3 build_dataset.py
"""

import csv
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))

# The "as of" date the series speaks from. All YTD figures are relative to this.
AS_OF = date(2026, 8, 25)

# Fiscal year starts February 1. This is what makes fiscal YTD != calendar YTD.
FISCAL_START_MONTH = 2


def write(name, header, rows):
    path = os.path.join(HERE, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:34s} {len(rows):4d} rows")


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

# region and industry are the attributes Part 2's "silent no-op" filter uses.
ACCOUNTS = [
    # id,     name,               region,    industry,             segment
    ("A-001", "Acme Corp",        "West",    "Manufacturing",      "Enterprise"),
    ("A-002", "Borealis Ltd",     "West",    "Technology",         "Enterprise"),
    ("A-003", "Cyan Systems",     "East",    "Technology",         "Mid-Market"),
    ("A-004", "Delta Foods",      "East",    "Retail",             "Enterprise"),
    ("A-005", "Everest Health",   "Central", "Healthcare",         "Enterprise"),
    ("A-006", "Fjord Logistics",  "West",    "Logistics",          "Mid-Market"),
    ("A-007", "Granite Bank",     "East",    "Financial Services", "Enterprise"),
    ("A-008", "Helios Energy",    "Central", "Energy",             "Enterprise"),
    ("A-009", "Ionic Labs",       "West",    "Life Sciences",      "Mid-Market"),
    ("A-010", "Juniper Retail",   "Central", "Retail",             "Mid-Market"),
]

USERS = [
    # id,     name,          role,               region
    ("U-001", "Ana Ruiz",    "Account Executive", "West"),
    ("U-002", "Ben Okafor",  "Account Executive", "East"),
    ("U-003", "Chen Wei",    "Account Executive", "Central"),
    ("U-004", "Dara Singh",  "Senior AE",         "West"),
]

PRODUCTS = [
    # id,     name,               family,     list_price
    ("P-001", "Widget",           "Hardware", 1000),
    ("P-002", "Gadget",           "Hardware", 2500),
    ("P-003", "Gizmo",            "Hardware", 5000),
    ("P-004", "Platform License", "Software", 20000),
    ("P-005", "Support Plan",     "Services", 5000),
    ("P-006", "Training Credits", "Services", 500),
]

# ---------------------------------------------------------------------------
# Fact: Opportunities  (grain = one row per opportunity)
# ---------------------------------------------------------------------------
# Amounts are chosen so that:
#   Closed Won   = 400,000 (4 opps)
#   Closed Lost  = 600,000 (4 opps)   -> Closed total 1,000,000 (8 opps)
#   Open         = 250,000 (3 opps)   -> All total    1,250,000 (11 opps)
# which yields win rates of 40% / 32% (by value) and 50% / 36.4% (by count).
#
# Accounts are deliberately concentrated so the chasm trap has something to chew on,
# and so the whitespace quadrants are all populated.
OPPORTUNITIES = [
    # id,     name,                        account, owner,   stage,        amount,  close_date,   created_date
    ("O-001", "Acme Platform Expansion",   "A-001", "U-001", "Proposal",    100000, "2026-11-15", "2026-07-01"),
    ("O-002", "Borealis Support Renewal",  "A-002", "U-001", "Negotiation",  75000, "2026-10-30", "2026-06-15"),
    ("O-003", "Cyan Net-New Platform",     "A-003", "U-002", "Discovery",    75000, "2026-12-20", "2026-08-01"),
    ("O-004", "Delta Widget Rollout",      "A-001", "U-002", "Closed Won",  150000, "2026-05-20", "2026-01-10"),
    ("O-005", "Everest Training Bundle",   "A-004", "U-003", "Closed Won",  120000, "2026-06-12", "2026-02-01"),
    ("O-006", "Fjord Gadget Fleet",        "A-005", "U-004", "Closed Won",   80000, "2026-01-16", "2025-10-20"),
    ("O-007", "Granite Support Plan",      "A-006", "U-002", "Closed Won",   50000, "2026-07-08", "2026-03-05"),
    ("O-008", "Helios Platform Bid",       "A-002", "U-003", "Closed Lost", 200000, "2026-06-30", "2026-02-10"),
    ("O-009", "Ionic Gizmo Pilot",         "A-004", "U-004", "Closed Lost", 175000, "2026-05-05", "2026-01-15"),
    ("O-010", "Juniper Retail Refresh",    "A-005", "U-003", "Closed Lost", 125000, "2026-07-22", "2026-03-01"),
    ("O-011", "Acme Services Add-on",      "A-001", "U-001", "Closed Lost", 100000, "2026-03-14", "2025-12-01"),
]

# ---------------------------------------------------------------------------
# Junction: Opportunity Line Items  (grain = one row per product per opportunity)
# ---------------------------------------------------------------------------
# O-001 has exactly three lines summing to its $100,000 header amount. That single
# opportunity carries both the fan-out lesson (3 x 100,000 = 300,000) and the
# allocation lesson (equal split 33,333 each vs. by-line 40,000/35,000/25,000).
OPP_LINES = [
    # id,      opportunity, product, quantity, line_amount
    ("OLI-01", "O-001", "P-001",  40,  40000),
    ("OLI-02", "O-001", "P-004",   2,  35000),
    ("OLI-03", "O-001", "P-005",   5,  25000),
    ("OLI-04", "O-002", "P-005",  15,  75000),
    ("OLI-05", "O-003", "P-004",   3,  60000),
    ("OLI-06", "O-003", "P-006",  30,  15000),
    ("OLI-07", "O-004", "P-001", 100, 100000),
    ("OLI-08", "O-004", "P-002",  20,  50000),
    ("OLI-09", "O-005", "P-006", 240, 120000),
    ("OLI-10", "O-006", "P-002",  32,  80000),
    ("OLI-11", "O-007", "P-005",  10,  50000),
    ("OLI-12", "O-008", "P-004",  10, 200000),
    ("OLI-13", "O-009", "P-003",  35, 175000),
    ("OLI-14", "O-010", "P-001", 125, 125000),
    ("OLI-15", "O-011", "P-005",  12,  60000),
    ("OLI-16", "O-011", "P-006",  80,  40000),
]

# ---------------------------------------------------------------------------
# Fact: Orders  (grain = one row per order)
# ---------------------------------------------------------------------------
# Total bookings = 600,000. A-007 has an order but no opportunity at all, which is
# what makes the naive inner join *drop* a row as well as inflate the others.
ORDERS = [
    # id,     account, order_date,   amount
    ("R-001", "A-001", "2026-02-10",  60000),
    ("R-002", "A-001", "2026-05-22",  90000),
    ("R-003", "A-001", "2026-08-14",  50000),
    ("R-004", "A-002", "2026-03-05",  40000),
    ("R-005", "A-002", "2026-07-19",  60000),
    # R-006 sits in January on purpose: it is inside the calendar year and outside the
    # fiscal one, and it is the entire $120,000 gap in the Part 7 YTD trap.
    ("R-006", "A-004", "2026-01-20", 120000),
    ("R-007", "A-005", "2026-06-25",  80000),
    ("R-008", "A-006", "2026-03-30",  45000),
    ("R-009", "A-007", "2026-08-20",  55000),
]

# ---------------------------------------------------------------------------
# Order Lines  (grain = one row per product per order)
# ---------------------------------------------------------------------------
# Product coverage is tuned for the product-level whitespace lesson:
#   P-002 Gadget and P-003 Gizmo sell but are absent from open pipeline.
#   P-006 Training Credits sits in open pipeline but has never sold.
ORDER_LINES = [
    # id,     order,   product, quantity, line_amount
    ("OL-01", "R-001", "P-001",  60,  60000),
    ("OL-02", "R-002", "P-002",  20,  50000),
    ("OL-03", "R-002", "P-004",   2,  40000),
    ("OL-04", "R-003", "P-005",  10,  50000),
    ("OL-05", "R-004", "P-001",  40,  40000),
    ("OL-06", "R-005", "P-003",  12,  60000),
    ("OL-07", "R-006", "P-002",  28,  70000),
    ("OL-08", "R-006", "P-004",   3,  50000),
    ("OL-09", "R-007", "P-001",  80,  80000),
    ("OL-10", "R-008", "P-005",   9,  45000),
    ("OL-11", "R-009", "P-003",  11,  55000),
]


def fiscal_year(d):
    """Fiscal year label. FY starts Feb 1, so Jan 2026 belongs to FY2026."""
    return d.year + 1 if d.month >= FISCAL_START_MONTH else d.year


def fiscal_quarter(d):
    offset = (d.month - FISCAL_START_MONTH) % 12
    return offset // 3 + 1


def build_calendar():
    """A real date dimension, materialized once by 'the builder'.

    This is the table Part 1 draws as 'Date' and never explains, and the table Part 7's
    YTD trap depends on. Both fiscal and calendar attributes live here so that
    'this year' is a modeling decision rather than a guess.
    """
    rows = []
    d = date(2025, 10, 1)
    end = date(2027, 1, 31)
    while d <= end:
        fy = fiscal_year(d)
        fq = fiscal_quarter(d)
        rows.append((
            d.isoformat(),
            d.year,
            d.month,
            d.strftime("%B"),
            (d.month - 1) // 3 + 1,
            f"{d.year}-{d.month:02d}",
            fy,
            fq,
            f"FY{fy}-Q{fq}",
            # Two YTD flags. The whole Part 7 lesson is that these disagree.
            "TRUE" if (d.year == AS_OF.year and d <= AS_OF) else "FALSE",
            "TRUE" if (fy == fiscal_year(AS_OF) and d <= AS_OF) else "FALSE",
        ))
        d += timedelta(days=1)
    return rows


def main():
    print("Building dataset in", HERE)

    write("accounts.csv",
          ["account_id", "account_name", "region", "industry", "segment"],
          ACCOUNTS)

    write("users.csv",
          ["user_id", "user_name", "role", "region"],
          USERS)

    write("products.csv",
          ["product_id", "product_name", "product_family", "list_price"],
          PRODUCTS)

    write("calendar.csv",
          ["date", "calendar_year", "month_number", "month_name", "calendar_quarter",
           "year_month", "fiscal_year", "fiscal_quarter", "fiscal_period",
           "is_calendar_ytd", "is_fiscal_ytd"],
          build_calendar())

    write("opportunities.csv",
          ["opportunity_id", "opportunity_name", "account_id", "owner_user_id",
           "stage", "amount", "close_date", "created_date"],
          OPPORTUNITIES)

    write("opportunity_line_items.csv",
          ["line_item_id", "opportunity_id", "product_id", "quantity", "line_amount"],
          OPP_LINES)

    write("orders.csv",
          ["order_id", "account_id", "order_date", "amount"],
          ORDERS)

    write("order_lines.csv",
          ["order_line_id", "order_id", "product_id", "quantity", "line_amount"],
          ORDER_LINES)

    print("Done. Run verify_numbers.py to check every figure quoted in the series.")


if __name__ == "__main__":
    main()
