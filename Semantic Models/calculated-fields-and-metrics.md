# Calculated Fields & Metrics
*The governed metrics from the series, in the form the Tableau Next API actually takes.*

Back to [series overview](../README.md) · Model spec:
[`sales-pipeline-model.yaml`](sales-pipeline-model.yaml)

---

## Before you run anything: discover the real field names

The single most common failure when creating calculated fields is referencing a field name that
doesn't exist. Depending on how the model was assembled, `Amount` may surface as `Amount`,
`Amount1`, or something else entirely. **Never guess — inspect first.**

```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')

# What models exist?
python scripts/discover_sdm.py --list

# What is actually in ours?
python scripts/discover_sdm.py --sdm Sales_Pipeline_And_Bookings --json
```

In the output, `semanticDataObjects[].objectName` gives you the table names to use in qualified
references, and `semanticMeasurements` / `semanticDimensions` give you the field names.

Two syntax rules that account for most validation errors:

| Kind of field | Syntax | Example |
|---|---|---|
| Table field | **qualified** | `[Opportunity_TAB_Sales_Pipeline].[Amount]` |
| Calculated field (`_clc`) | **unqualified** — they are model-level | `[Win_Rate_by_Value_clc]` |

And two naming rules: calculated fields must end `_clc`, metrics must end `_mtc`, and no API
name may contain a double underscore.

Throughout this file the object names are written as `Opportunity_TAB_Sales_Pipeline`,
`Order_TAB_Sales_Pipeline` and so on. **Substitute whatever `discover_sdm.py` actually returns
for your org.**

---

## The `UserAgg` rule

Every ratio below uses `--aggregation UserAgg`, and it is not optional.

When an expression already contains aggregation functions, `UserAgg` tells the engine that the
expression handles its own aggregation. Choose `Sum` or `Avg` instead and the engine wraps a
second aggregation *around* an already-aggregated result — which is the `SUM(a/b)` error from
Part 5, arrived at through a configuration setting rather than a formula. The expression looks
perfect and the number is wrong.

Rule of thumb: **if your expression contains `SUM(`, its aggregation type is `UserAgg`.**

---

## 1. Open Pipeline

Additive, and the baseline for everything else. Expressed as "not closed" rather than listing
open stages, so a newly added stage doesn't silently fall out of the pipeline.

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Open_Pipeline_clc \
  --label "Open Pipeline" \
  --expression "SUM(IF [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Won' OR [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Lost' THEN 0 ELSE [Opportunity_TAB_Sales_Pipeline].[Amount] END)" \
  --aggregation UserAgg
```

Expected against the sample data: **$250,000**.

---

## 2. Bookings

Comes from `Order`, never from `Opportunity`. The description is doing real work here — it is
what stops an agent answering a bookings question from the pipeline fact.

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Bookings_clc \
  --label "Bookings" \
  --expression "SUM([Order_TAB_Sales_Pipeline].[Amount])" \
  --aggregation Sum
```

Expected: **$600,000**.

---

## 3. Win Rate by Value — the house default

The ratio of sums. Note `UserAgg`, and note that the denominator constraint lives *inside* the
expression rather than relying on the caller to filter to closed opportunities.

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Win_Rate_by_Value_clc \
  --label "Win Rate by Value" \
  --expression "SUM(IF [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Won' THEN [Opportunity_TAB_Sales_Pipeline].[Amount] ELSE 0 END) / SUM(IF [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Won' OR [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Lost' THEN [Opportunity_TAB_Sales_Pipeline].[Amount] ELSE 0 END)" \
  --aggregation UserAgg
```

Expected: **40.0%**.

Description to set on the field, verbatim — this is what the agent reads:

> Won amount divided by closed amount. Excludes open opportunities, so it measures competitive
> performance on decided deals. HOUSE DEFAULT — an unqualified request for "win rate" resolves
> to this. Never sum or average this field; recompute it.

---

## 4. Win Rate by Count — the named sibling

Same shape, counting deals instead of money. Publishing both, with distinct names, is the
governance fix from Part 6.

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Win_Rate_by_Count_clc \
  --label "Win Rate by Count" \
  --expression "SUM(IF [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Won' THEN 1 ELSE 0 END) / SUM(IF [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Won' OR [Opportunity_TAB_Sales_Pipeline].[Stage] = 'Closed Lost' THEN 1 ELSE 0 END)" \
  --aggregation UserAgg
```

Expected: **50.0%**.

A 10-point gap from Win Rate by Value on the same data, because our losses are larger than our
wins. That gap is the reason both metrics have to exist.

---

## 5. The two YTD metrics

The default and its first-class sibling. Both are real metrics; neither is a workaround.

```bash
# House default for "this year"
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Bookings_Fiscal_YTD_clc \
  --label "Bookings Fiscal YTD" \
  --expression "SUM(IF [Date_TAB_Sales_Pipeline].[Is_Fiscal_Ytd] = 'TRUE' THEN [Order_TAB_Sales_Pipeline].[Amount] ELSE 0 END)" \
  --aggregation UserAgg

# Named sibling, for the board and anyone who thinks in calendar years
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Bookings_Calendar_YTD_clc \
  --label "Bookings Calendar YTD" \
  --expression "SUM(IF [Date_TAB_Sales_Pipeline].[Is_Calendar_Ytd] = 'TRUE' THEN [Order_TAB_Sales_Pipeline].[Amount] ELSE 0 END)" \
  --aggregation UserAgg
```

Expected: **$480,000** fiscal, **$600,000** calendar — a $120,000, 20% gap.

The `= 'TRUE'` comparison assumes the YTD flags land as text, which is how they appear in
[`../data/calendar.csv`](../data/calendar.csv). If your loader types them as boolean, use the
field directly (`IF [Date_TAB_Sales_Pipeline].[Is_Fiscal_Ytd] THEN ...`). Check the data type in
the `discover_sdm.py` output rather than assuming.

A more robust alternative, if you'd rather not depend on precomputed flags, is to derive the
window from the fiscal year attribute — but precomputing the flag in the calendar table is
cheaper at query time and, per Part 5, that is the right place for stable row-level logic.

---

## 6. Allocation factor on the bridge

The field that stops "revenue by product" exceeding total revenue. It lives on the
`Opportunity_Line_Item` bridge, which is where attributes of the *relationship* belong.

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Pipeline_And_Bookings \
  --type measurement \
  --name Allocation_Factor_clc \
  --label "Allocation Factor" \
  --expression "SUM([Opportunity_Line_Item_TAB_Sales_Pipeline].[Line_Amount]) / SUM([Opportunity_TAB_Sales_Pipeline].[Amount])" \
  --aggregation UserAgg
```

For opportunity O-001 this yields **0.40 / 0.35 / 0.25**, summing to exactly **1.00**. That
sum-to-one property is the whole point: it is what makes allocated revenue reconcile to total
revenue.

The test to run after creating it: put revenue by product on screen and total the column. It must
equal total revenue. If it's larger, all-or-nothing attribution has crept in somewhere.

---

## 7. Wrapping the defaults as metrics

Metrics (`_mtc`) are lightweight wrappers for dashboard KPI widgets. They reference an existing
calculated field, so **create the calculated field first** — a metric pointing at a field that
doesn't exist yet fails with a "field not found" error.

Note the time dimension choice on each, which is the role-playing decision from Part 2 made
explicit: bookings key off `Order_Date`, win rate off `Close_Date`.

```bash
python scripts/create_metric.py \
  --sdm Sales_Pipeline_And_Bookings \
  --name Bookings_mtc \
  --label "Bookings" \
  --calculated-field Bookings_clc \
  --time-field Order_Date \
  --time-table Order_TAB_Sales_Pipeline \
  --additional-dimension "Account_Name:Account_TAB_Sales_Pipeline" \
  --additional-dimension "Region:Account_TAB_Sales_Pipeline" \
  --additional-dimension "Product_Family:Product_TAB_Sales_Pipeline"

python scripts/create_metric.py \
  --sdm Sales_Pipeline_And_Bookings \
  --name Win_Rate_by_Value_mtc \
  --label "Win Rate by Value" \
  --calculated-field Win_Rate_by_Value_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Pipeline \
  --additional-dimension "Region:Account_TAB_Sales_Pipeline" \
  --additional-dimension "User_Name:User_TAB_Sales_Pipeline"

python scripts/create_metric.py \
  --sdm Sales_Pipeline_And_Bookings \
  --name Open_Pipeline_mtc \
  --label "Open Pipeline" \
  --calculated-field Open_Pipeline_clc \
  --time-field Created_Date \
  --time-table Opportunity_TAB_Sales_Pipeline \
  --additional-dimension "Account_Name:Account_TAB_Sales_Pipeline" \
  --additional-dimension "User_Name:User_TAB_Sales_Pipeline"
```

`Open_Pipeline_mtc` deliberately uses `Created_Date` — pipeline generation is a question about
when a deal *entered* the pipeline, not when it's forecast to close.

---

## Validate before you POST

Every script supports `--dry-run`, which prints the payload without sending it:

```bash
python scripts/create_calc_field.py ... --dry-run
```

Check four things in the output: the expression syntax, that every referenced field exists in the
`discover_sdm.py` output, that the aggregation type matches the expression (`UserAgg` if it
contains `SUM`), and that the API name follows the `_clc` / `_mtc` convention with no double
underscores.

---

## Underlying endpoints

If you're calling the API directly rather than through the scripts:

```
GET  /services/data/v66.0/ssot/semantic/models
GET  /services/data/v66.0/ssot/semantic/models/{sdmName}
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-measurements
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-dimensions
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/metrics
```

All requests need `Authorization: Bearer {token}`.

---

## After creation: verify against the numbers

Creating a field successfully is not the same as creating a correct one. For each field above,
compare the value it returns against the expected value, all of which are asserted by
[`../data/verify_numbers.py`](../data/verify_numbers.py):

| Field | Expected |
|---|---|
| `Open_Pipeline_clc` | $250,000 |
| `Bookings_clc` | $600,000 |
| `Win_Rate_by_Value_clc` | 40.0% |
| `Win_Rate_by_Count_clc` | 50.0% |
| `Bookings_Fiscal_YTD_clc` | $480,000 |
| `Bookings_Calendar_YTD_clc` | $600,000 |
| `Allocation_Factor_clc` (O-001) | 0.40 / 0.35 / 0.25 |

Then run the [agent eval set](agent-eval-set.md), which tests the same definitions through
natural language rather than through the API.
