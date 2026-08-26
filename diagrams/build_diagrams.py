#!/usr/bin/env python3
"""
Generates every SVG diagram in the "Modeling for Answers" series.

Why a generator rather than hand-written SVG: SVG <text> does not wrap, so a fixed-width
box plus a font fallback wider than the author's font silently overflows. That bug shipped
in an earlier hand-written diagram. Here, every label is measured against its container and
the build FAILS loudly if it would not fit, so the defect class cannot recur.

All figures shown in these diagrams come from ../data/ and are asserted by
../data/verify_numbers.py.

Run:  python3 build_diagrams.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "Helvetica, Arial, sans-serif")

# Palette, carried over from the original hand-drawn diagrams.
NAVY = "#1f4e79"
NAVY_SOFT = "#e8eef5"
NAVY_TEXT = "#cfe0f0"
INK = "#0f172a"
MUTED = "#475569"
FAINT = "#64748b"
LINE = "#94a3b8"
SLATE_BG = "#f1f5f9"
GREEN = "#059669"
GREEN_BG = "#dcfce7"
GREEN_DK = "#065f46"
GREEN_TX = "#047857"
RED = "#dc2626"
RED_BG = "#fee2e2"
AMBER = "#b45309"
AMBER_BG = "#fef3c7"
WHITE = "#ffffff"

# ---------------------------------------------------------------------------
# Text measurement
# ---------------------------------------------------------------------------
# Approximate advance widths in em, by character class, for a UI sans-serif.
_NARROW = set("iljtfIr.,:;'`!|()[]{}-")
_WIDE = set("mMW@%")
_CAPS = set("ABCDEFGHJKLNOPQRSTUVXYZ0123456789$&")

# Fallback fonts (DejaVu Sans, Liberation Sans) run wider than -apple-system.
# Everything is measured with this safety multiplier so the diagrams survive
# rendering anywhere.
FALLBACK_SAFETY = 1.14

_WEIGHT_SCALE = {400: 1.0, 500: 1.02, 600: 1.06, 700: 1.10}


def text_width(s, size, weight=400):
    em = 0.0
    for ch in s:
        if ch == " ":
            em += 0.28
        elif ch in _NARROW:
            em += 0.31
        elif ch in _WIDE:
            em += 0.88
        elif ch in _CAPS:
            em += 0.63
        else:
            em += 0.53
    return em * size * _WEIGHT_SCALE.get(weight, 1.0) * FALLBACK_SAFETY


_problems = []
_current = "?"


def fit(label, s, size, weight, available, where):
    """Record an overflow instead of shipping one."""
    w = text_width(s, size, weight)
    if w > available:
        _problems.append(
            f"{_current} [{where}/{label}] needs {w:.0f}px, has {available:.0f}px: {s!r}")
    return s


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, size=13, weight=400, fill=INK, anchor="middle", opacity=None):
    o = f' opacity="{opacity}"' if opacity else ""
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{o}>{esc(s)}</text>')


def rect(x, y, w, h, fill=WHITE, stroke=None, sw=1.5, rx=10, dash=None):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}{d}/>'


def line(x1, y1, x2, y2, stroke=LINE, sw=2, dash=None, arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a = ' marker-end="url(#arrow)"' if arrow else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}{a}/>')


def node(x, y, w, h, title, sub=None, sub2=None, fill=NAVY_SOFT, stroke=NAVY,
         title_fill=INK, sub_fill=FAINT, dash=None, where="node"):
    """A labeled box. Title and subtitles are measured against the box width."""
    pad = 16
    avail = w - 2 * pad
    out = [rect(x, y, w, h, fill=fill, stroke=stroke, dash=dash)]
    cx = x + w / 2
    if sub2:
        ty, sy, s2y = y + h / 2 - 12, y + h / 2 + 6, y + h / 2 + 24
    elif sub:
        ty, sy, s2y = y + h / 2 - 4, y + h / 2 + 16, None
    else:
        ty, sy, s2y = y + h / 2 + 6, None, None
    out.append(txt(cx, ty, fit("title", title, 16, 700, avail, where), 16, 700, title_fill))
    if sub:
        out.append(txt(cx, sy, fit("sub", sub, 12, 500, avail, where), 12, 500, sub_fill))
    if sub2:
        out.append(txt(cx, s2y, fit("sub2", sub2, 12, 500, avail, where), 12, 500, sub_fill))
    return "".join(out)


def pill(x, y, s, size=12, weight=600, fill=NAVY, bg=WHITE, where="pill"):
    """A small label with a background plate, for placing on top of a connector."""
    w = text_width(s, size, weight) + 14
    h = size + 9
    return (rect(x - w / 2, y - h / 2, w, h, fill=bg, rx=4) +
            txt(x, y + size * 0.36, s, size, weight, fill))


def heading(w, title, subtitle=None, size=22):
    out = [txt(w / 2, 38, fit("title", title, size, 700, w - 60, "heading"),
               size, 700, INK)]
    if subtitle:
        out.append(txt(w / 2, 62, fit("subtitle", subtitle, 14, 400, w - 40, "heading"),
                       14, 400, MUTED))
    return "".join(out)


def footnote(w, y, s, size=13, fill=MUTED, weight=400):
    return txt(w / 2, y, fit("footnote", s, size, weight, w - 40, "footnote"),
               size, weight, fill)


DEFS = ('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{LINE}"/></marker></defs>')


def svg(name, w, h, title, desc, body):
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'role="img" aria-labelledby="t d" font-family="{FONT}">'
           f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
           f'{DEFS}<rect width="{w}" height="{h}" fill="{WHITE}"/>'
           f'{body}</svg>\n')
    with open(os.path.join(HERE, name), "w") as fh:
        fh.write(doc)
    print(f"  {name}")


def table(x, y, col_w, rows, row_h=28, header_fill=NAVY, header_text=WHITE,
          body_fill=WHITE, alt_fill=SLATE_BG, stroke=LINE, sizes=None,
          weights=None, fills=None, where="table"):
    """A simple data grid. rows[0] is the header. col_w is a list of widths."""
    out = []
    total_w = sum(col_w)
    for r, row in enumerate(rows):
        ry = y + r * row_h
        is_head = r == 0
        bg = header_fill if is_head else (body_fill if r % 2 else alt_fill)
        out.append(rect(x, ry, total_w, row_h, fill=bg, stroke=stroke, sw=1, rx=0))
        cx = x
        for c, cell in enumerate(row):
            size = 12 if is_head else (sizes[r][c] if sizes else 12)
            weight = 700 if is_head else (weights[r][c] if weights else 400)
            fill = header_text if is_head else (fills[r][c] if fills else INK)
            out.append(txt(cx + col_w[c] / 2, ry + row_h / 2 + size * 0.36,
                           fit(f"cell{r},{c}", str(cell), size, weight,
                               col_w[c] - 12, where),
                           size, weight, fill))
            cx += col_w[c]
    return "".join(out)


# ===========================================================================
# PART 1
# ===========================================================================

def part1_star():
    W, H = 780, 470
    b = [heading(W, "Star schema: one fact, dimensions around it",
                 "Simple to read, fast to query, easy for people and agents to navigate")]
    fx, fy, fw, fh = 300, 218, 180, 78
    cx, cy = fx + fw / 2, fy + fh / 2
    dims = [(60, 118, "Account", "who"), (540, 118, "User", "owner"),
            (60, 348, "Product", "what"), (540, 348, "Date", "when")]
    for dx, dy, _, _ in dims:
        b.append(line(cx, cy, dx + 90, dy + 32))
    b.append(node(fx, fy, fw, fh, "Opportunities", "FACT \u00b7 pipeline",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p1 fact"))
    for dx, dy, name, role in dims:
        b.append(node(dx, dy, 180, 64, name, role, where=f"p1 {name}"))
    b.append(footnote(W, 442, "Grain: one row per opportunity \u2014 state it out loud, "
                              "and never let a query change it."))
    svg("part-1-01-star-schema.svg", W, H,
        "Star schema",
        "The Opportunities fact in the center, connected to four dimensions - Account, "
        "User, Product and Date - arranged around it like the points of a star. A footnote "
        "states the grain: one row per opportunity.",
        "".join(b))


def part1_wide_table():
    W, H = 820, 470
    b = [heading(W, "Why one big table confuses the agent",
                 "Five amount-like columns, no structure, and nothing to say which is "
                 "the real measure")]
    cols = ["Amount", "Expected Rev", "ACV", "TCV", "Weighted Amt"]
    rows = [cols,
            ["100,000", "65,000", "80,000", "240,000", "65,000"],
            ["75,000", "56,250", "60,000", "180,000", "56,250"],
            ["75,000", "18,750", "75,000", "225,000", "18,750"]]
    col_w = [124, 124, 124, 124, 124]
    b.append(table(90, 108, col_w, rows, row_h=30, where="p1 wide"))
    b.append(rect(90, 238, 620, 46, fill=RED_BG, stroke=RED, sw=1.5))
    b.append(txt(400, 267, fit("q", "Agent: \u201cwhat is my open pipeline?\u201d \u2014 "
                               "which column did you mean?", 14, 600, 596, "p1 q"),
                 14, 600, RED))
    b.append(txt(400, 322, "To a person, context disambiguates these.", 14, 400, MUTED))
    b.append(txt(400, 344, "To an agent reading bare column names, they are "
                           "interchangeable \u2014 so it guesses.", 14, 400, MUTED))
    b.append(rect(150, 370, 500, 62, fill=GREEN_BG, stroke=GREEN, sw=1.5))
    b.append(txt(400, 394, "The fix is not to hide the ambiguity in a wider table.",
                 13, 600, GREEN_DK))
    b.append(txt(400, 416, "Model the fact separately, then label every field (Part 7).",
                 13, 400, GREEN_TX))
    svg("part-1-02-one-big-table-trap.svg", W, H,
        "The one big table trap",
        "A wide flat table with five similarly named amount columns. An agent asked for "
        "open pipeline has no structural cue about which column is the real measure, so "
        "it guesses. The fix is a modeled fact plus labeled fields.",
        "".join(b))


def part1_scd():
    W, H = 860, 520
    b = [heading(W, "Slowly changing dimensions: Type 1 or Type 2?",
                 "Acme Corp moves from the West region to the East on 1 June 2026")]
    # Type 1
    b.append(rect(40, 96, 370, 46, fill=NAVY, stroke=NAVY))
    b.append(txt(225, 125, "Type 1 \u2014 overwrite", 16, 700, WHITE))
    rows1 = [["Account", "Region"], ["Acme Corp", "East"]]
    b.append(table(40, 152, [185, 185], rows1, row_h=30, where="p1 scd1"))
    b.append(txt(225, 266, "One row. The old value is gone.", 13, 500, MUTED))
    b.append(rect(40, 284, 370, 84, fill=RED_BG, stroke=RED, sw=1.5))
    b.append(txt(225, 310, "Last quarter's \u201cWest pipeline\u201d", 13, 600, RED))
    b.append(txt(225, 331, "changes retroactively. History is", 13, 400, MUTED))
    b.append(txt(225, 351, "restated every time an attribute moves.", 13, 400, MUTED))
    # Type 2
    b.append(rect(450, 96, 370, 46, fill=GREEN, stroke=GREEN))
    b.append(txt(635, 125, "Type 2 \u2014 versioned", 16, 700, WHITE))
    rows2 = [["Region", "From", "To", "Current"],
             ["West", "2020-01-01", "2026-05-31", "No"],
             ["East", "2026-06-01", "9999-12-31", "Yes"]]
    b.append(table(450, 152, [92, 105, 105, 68], rows2, row_h=30, where="p1 scd2"))
    b.append(txt(635, 266, "Two rows, with effective dates.", 13, 500, MUTED))
    b.append(rect(450, 284, 370, 84, fill=GREEN_BG, stroke=GREEN, sw=1.5))
    b.append(txt(635, 310, "Last quarter still reports West.", 13, 600, GREEN_DK))
    b.append(txt(635, 331, "The fact joins to the version that was", 13, 400, GREEN_TX))
    b.append(txt(635, 351, "in effect on its own close date.", 13, 400, GREEN_TX))
    b.append(footnote(W, 416, "Choose deliberately \u2014 it is a business question, "
                              "not a technical one.", 14, INK, 600))
    b.append(footnote(W, 444, "Type 1 for corrections (a misspelled name). "
                              "Type 2 when the change is itself a fact you report on"))
    b.append(footnote(W, 468, "(territory moves, segment reclassification, owner changes)."))
    svg("part-1-03-scd-type-1-vs-type-2.svg", W, H,
        "Slowly changing dimensions, Type 1 versus Type 2",
        "Acme Corp moves from West to East. Under Type 1 the region is overwritten, so "
        "prior-period reports are restated. Under Type 2 a second row is added with "
        "effective dates, so history is preserved and each fact joins to the version in "
        "effect at the time.",
        "".join(b))


# ===========================================================================
# PART 2
# ===========================================================================

def part2_cardinality():
    W, H = 800, 490
    b = [heading(W, "Declare cardinality on every relationship",
                 "Many-to-one is the safe case: many facts roll up to one dimension member")]
    fx, fy, fw, fh = 310, 226, 180, 78
    cx, cy = fx + fw / 2, fy + fh / 2
    dims = [(60, 122, "Account"), (560, 122, "User"),
            (60, 352, "Product"), (560, 352, "Date")]
    for dx, dy, _ in dims:
        b.append(line(cx, cy, dx + 90, dy + 32))
    # Cardinality pills sit at the midpoint of each connector.
    for dx, dy, name in dims:
        mx, my = (cx + dx + 90) / 2, (cy + dy + 32) / 2
        b.append(pill(mx, my, "many \u2192 1", where=f"p2 card {name}"))
    b.append(node(fx, fy, fw, fh, "Opportunities", "the \u201cmany\u201d side",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p2 fact"))
    for dx, dy, name in dims:
        b.append(node(dx, dy, 180, 64, name, "the \u201cone\u201d side",
                      where=f"p2 {name}"))
    b.append(footnote(W, 452, "Wrong cardinality produces numbers that look plausible "
                              "and are wrong \u2014 the most dangerous kind."))
    svg("part-2-01-cardinality.svg", W, H,
        "Star schema with cardinality declared",
        "The same star schema with every relationship labeled many-to-one: many "
        "Opportunities relate to one Account, one User, one Product and one Date.",
        "".join(b))


def part2_no_op():
    W, H = 820, 430
    b = [heading(W, "Why the filter did nothing",
                 "Queries are economical \u2014 they will not cross a relationship "
                 "unless a field forces them to")]
    # The question. Widened generously; this is the box that overflowed before.
    b.append(rect(210, 92, 400, 56, fill=INK, stroke=INK))
    b.append(txt(410, 116, fit("q1", "Question: SUM(Amount) by Close Date",
                               14, 600, 372, "p2 q"), 14, 600, WHITE))
    b.append(txt(410, 136, "every field lives on Opportunity", 12, 400, LINE))
    b.append(line(410, 148, 250, 236, GREEN, 2.5))
    b.append(line(410, 148, 570, 236, "#cbd5e1", 2.5, dash="7 6"))
    b.append(pill(505, 196, "not traversed", 12, 700, RED, WHITE, where="p2 nt"))
    # Visited
    b.append(rect(100, 238, 300, 104, fill=GREEN_BG, stroke=GREEN, sw=2))
    b.append(txt(250, 268, "Opportunity", 17, 700, GREEN_DK))
    b.append(txt(250, 292, "visited \u2014 Amount and Close Date", 12, 500, GREEN_TX))
    b.append(txt(250, 312, "both live here, so the query", 12, 400, GREEN_TX))
    b.append(txt(250, 330, "answers entirely from this object", 12, 400, GREEN_TX))
    # Not visited
    b.append(rect(420, 238, 300, 104, fill=SLATE_BG, stroke=LINE, sw=2, dash="6 5"))
    b.append(txt(570, 268, "Account", 17, 700, FAINT))
    b.append(txt(570, 292, "Filter: Region = West", 12, 700, RED))
    b.append(txt(570, 312, "never visited, so the filter", 12, 400, FAINT))
    b.append(txt(570, 330, "has no rows to act on", 12, 400, FAINT))
    b.append(footnote(W, 380, "Fix: put an Account field in the view, or promote the "
                              "filter into context (Part 6),"))
    b.append(footnote(W, 402, "so the query is obliged to travel to Account."))
    svg("part-2-02-silent-no-op.svg", W, H,
        "The silent no-op filter",
        "A query referencing only fields on Opportunity never travels to Account, so a "
        "Region filter placed on Account has nothing to act on and silently does nothing. "
        "The fix is to reference an Account field or promote the filter into context.",
        "".join(b))


def part2_role_playing():
    W, H = 900, 610
    b = [heading(W, "Role-playing dimensions: one calendar, three aliases",
                 "\u201cThis quarter\u201d is ambiguous until you say which date you mean")]

    # Facts on top, each relating down to role aliases rather than to one shared Date.
    b.append(node(238, 100, 200, 72, "Opportunity", "FACT",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p2rp opp"))
    b.append(node(575, 100, 200, 72, "Order", "FACT",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p2rp order"))

    aliases = [(135, "Date (Created)", "pipeline entered", 338, "CreatedDate"),
               (360, "Date (Closed)", "revenue booked", 338, "CloseDate"),
               (585, "Date (Order)", "order shipped", 675, "OrderDate")]
    for ax, title, sub, fact_cx, key in aliases:
        acx = ax + 90
        b.append(line(fact_cx, 172, acx, 250, LINE, 2, arrow=True))
        b.append(node(ax, 250, 180, 78, title, sub, where=f"p2rp {title}"))
        # Each alias hangs off the one physical calendar underneath it.
        b.append(line(acx, 328, 450, 400, LINE, 1.5, dash="5,4"))
        b.append(pill((fact_cx + acx) / 2, 211, key, where=f"p2rp key {key}"))

    b.append(node(320, 400, 260, 72, "Date", "one physical calendar DMO",
                  fill=SLATE_BG, stroke=LINE, dash="5,4", where="p2rp physical"))
    b.append(pill(450, 364, "same DMO", fill=FAINT, where="p2rp same"))

    b.append(rect(80, 500, 740, 68, fill=AMBER_BG, stroke=AMBER, sw=1.5))
    b.append(txt(450, 524, "One physical calendar. Three role aliases. One relationship each.",
                 13, 600, AMBER))
    b.append(txt(450, 546, "Two relationships to a single Date object would be a cycle \u2014 "
                           "so it isn't allowed.",
                 13, 400, MUTED))
    b.append(footnote(W, 590, "Leave the role implicit and two dashboards will quietly "
                              "choose differently."))
    svg("part-2-03-role-playing-dimension.svg", W, H,
        "Role-playing dimensions",
        "One physical Date calendar sits beneath three role aliases - Date (Created), "
        "Date (Closed) and Date (Order). Opportunity relates once to the Created alias and "
        "once to the Closed alias; Order relates once to the Order alias. Every alias "
        "points back at the same underlying calendar, so the definitions stay conformed "
        "while each relationship stays unambiguous.",
        "".join(b))


def part2_orphans():
    W, H = 860, 470
    b = [heading(W, "Referential integrity: the fact row with no dimension match",
                 "One opportunity carries an account id that is missing from the "
                 "Account table")]
    rows = [["Opportunity", "account_id", "Amount"],
            ["O-001 Acme Platform", "A-001", "$100,000"],
            ["O-002 Borealis Renewal", "A-002", "$75,000"],
            ["O-099 Orphaned Deal", "(missing)", "$40,000"]]
    fills = [[INK] * 3, [INK] * 3, [INK] * 3, [RED, RED, RED]]
    weights = [[700] * 3, [400] * 3, [400] * 3, [600] * 3]
    b.append(table(190, 100, [230, 130, 120], rows, row_h=30,
                   fills=fills, weights=weights, where="p2 orphan"))
    b.append(rect(60, 234, 340, 96, fill=RED_BG, stroke=RED, sw=1.5))
    b.append(txt(230, 260, "Inner join to Account", 14, 700, RED))
    b.append(txt(230, 284, "The orphan disappears.", 13, 400, MUTED))
    b.append(txt(230, 306, "Total reads $175,000 \u2014 and nothing", 13, 400, MUTED))
    b.append(txt(230, 324, "on screen says a row went missing.", 13, 400, MUTED))
    b.append(rect(430, 234, 370, 96, fill=GREEN_BG, stroke=GREEN, sw=1.5))
    b.append(txt(615, 260, "Outer join, or an Unknown member", 14, 700, GREEN_DK))
    b.append(txt(615, 284, "The orphan survives, bucketed as", 13, 400, GREEN_TX))
    b.append(txt(615, 306, "\u201cUnknown Account\u201d. Total reads", 13, 400, GREEN_TX))
    b.append(txt(615, 324, "$215,000 and the gap is visible.", 13, 400, GREEN_TX))
    b.append(footnote(W, 378, "Both totals are defensible. Only one of them tells you "
                              "the data has a problem.", 14, INK, 600))
    b.append(footnote(W, 406, "Give every conformed dimension an explicit Unknown "
                              "member and route orphans to it, so a broken"))
    b.append(footnote(W, 428, "key shows up as a number you can see rather than "
                              "revenue you cannot."))
    svg("part-2-04-orphan-rows.svg", W, H,
        "Referential integrity and orphan fact rows",
        "An opportunity whose account id is missing from the Account table. An inner join "
        "silently drops it and understates the total; an outer join or an explicit Unknown "
        "member keeps it visible so the data quality problem is apparent.",
        "".join(b))


# ===========================================================================
# PART 3
# ===========================================================================

def part3_fan_out():
    W, H = 840, 470
    b = [heading(W, "Fan-out: how one-to-many multiplies your money",
                 "One $100,000 opportunity, three line items, and a total of $300,000")]
    rows = [["Opportunity", "Line item", "Opportunity.Amount"],
            ["O-001 Acme Platform", "Widget", "$100,000"],
            ["O-001 Acme Platform", "Platform License", "$100,000"],
            ["O-001 Acme Platform", "Support Plan", "$100,000"],
            ["SUM", "", "$300,000"]]
    fills = [[INK] * 3, [INK] * 3, [INK] * 3, [INK] * 3, [RED, RED, RED]]
    weights = [[700] * 3, [400] * 3, [400] * 3, [400] * 3, [700] * 3]
    b.append(table(120, 100, [240, 200, 200], rows, row_h=32,
                   fills=fills, weights=weights, where="p3 fanout"))
    b.append(rect(120, 274, 300, 74, fill=GREEN_BG, stroke=GREEN, sw=1.5))
    b.append(txt(270, 300, "The truth", 14, 700, GREEN_DK))
    b.append(txt(270, 324, "$100,000", 20, 700, GREEN_DK))
    b.append(rect(440, 274, 320, 74, fill=RED_BG, stroke=RED, sw=1.5))
    b.append(txt(600, 300, "What the query returns", 14, 700, RED))
    b.append(txt(600, 324, "$300,000", 20, 700, RED))
    b.append(footnote(W, 384, "The join did not add money. It copied the header amount "
                              "onto every child row,", 14, INK, 600))
    b.append(footnote(W, 408, "and then you summed the copies. The line amounts "
                              "themselves are fine:"))
    b.append(footnote(W, 432, "$40,000 + $35,000 + $25,000 = $100,000. Only the header "
                              "amount was multiplied."))
    svg("part-3-01-grain-and-fan-out.svg", W, H,
        "Fan-out multiplies a header measure",
        "Opportunity O-001 has an amount of one hundred thousand dollars and three line "
        "items. Traversing the one-to-many relationship repeats the header amount on every "
        "child row, so summing it returns three hundred thousand dollars instead of one "
        "hundred thousand.",
        "".join(b))


def part3_chasm():
    W, H = 880, 560
    b = [heading(W, "The chasm trap: two facts, one shared dimension, no shared grain",
                 "Acme Corp has 3 orders and 3 opportunities \u2014 the join returns "
                 "9 rows")]
    b.append(node(60, 106, 220, 74, "Opportunities", "3 rows for Acme",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p3 opps"))
    b.append(node(600, 106, 220, 74, "Orders", "3 rows for Acme",
                  fill=NAVY, stroke=NAVY, title_fill=WHITE, sub_fill=NAVY_TEXT,
                  where="p3 orders"))
    b.append(node(330, 106, 220, 74, "Account", "shared dimension",
                  where="p3 acct"))
    b.append(line(280, 143, 330, 143, LINE, 2, arrow=True))
    b.append(line(600, 143, 550, 143, LINE, 2, arrow=True))
    b.append(rect(240, 208, 400, 46, fill=RED_BG, stroke=RED, sw=1.5))
    b.append(txt(440, 237, "3 \u00d7 3 = 9 rows, a partial Cartesian product",
                 14, 700, RED))
    rows = [["", "Alone (correct)", "After the join", "Inflation"],
            ["Bookings", "$600,000", "$1,245,000", "2.08x"],
            ["Opportunity value", "$1,250,000", "$2,150,000", "1.72x"]]
    fills = [[INK] * 4, [INK, GREEN_DK, RED, RED], [INK, GREEN_DK, RED, RED]]
    weights = [[700] * 4, [600, 600, 700, 700], [600, 600, 700, 700]]
    b.append(table(70, 276, [210, 200, 200, 130], rows, row_h=32,
                   fills=fills, weights=weights, where="p3 chasm"))
    b.append(rect(70, 388, 740, 96, fill=AMBER_BG, stroke=AMBER, sw=1.5))
    b.append(txt(460, 414, "And it does not only inflate \u2014 it silently discards.",
                 14, 700, AMBER))
    b.append(txt(460, 438, "Granite Bank has orders but no opportunities, so its "
                           "$55,000 vanishes.", 13, 400, MUTED))
    b.append(txt(460, 460, "Cyan Systems has an opportunity but no orders, so its "
                           "$75,000 vanishes too.", 13, 400, MUTED))
    b.append(footnote(W, 518, "Two facts can share a dimension without sharing a grain. "
                              "That is the whole problem."))
    svg("part-3-02-chasm-trap.svg", W, H,
        "The chasm trap",
        "Opportunities and Orders both relate to a shared Account dimension. Querying "
        "both together through Account pairs every order with every opportunity for that "
        "account, inflating bookings by 2.08 times and opportunity value by 1.72 times, "
        "while silently dropping accounts that appear in only one of the two facts.",
        "".join(b))


# ===========================================================================
# PART 4
# ===========================================================================

def part4_drill_across():
    W, H = 900, 580
    b = [heading(W, "Drill-across: aggregate first, then align on the conformed key",
                 "Each fact is summarized at its own grain before the two results meet")]
    b.append(txt(170, 100, "Step 1 \u2014 aggregate Opportunities", 13, 700, NAVY))
    r1 = [["Account", "Open pipeline"],
          ["Acme Corp", "$100,000"],
          ["Borealis Ltd", "$75,000"],
          ["Cyan Systems", "$75,000"]]
    b.append(table(30, 112, [150, 130], r1, row_h=28, where="p4 agg1"))
    b.append(txt(730, 100, "Step 1 \u2014 aggregate Orders", 13, 700, NAVY))
    r2 = [["Account", "Bookings"],
          ["Acme Corp", "$200,000"],
          ["Borealis Ltd", "$100,000"],
          ["Granite Bank", "$55,000"]]
    b.append(table(590, 112, [150, 130], r2, row_h=28, where="p4 agg2"))
    b.append(rect(330, 150, 240, 56, fill=GREEN, stroke=GREEN))
    b.append(txt(450, 174, "Step 2", 13, 700, WHITE))
    b.append(txt(450, 194, fit("j", "FULL OUTER JOIN on Account", 12, 600, 216,
                               "p4 join"), 12, 600, GREEN_BG))
    # Both arrows point into the join, which is the direction the data flows.
    b.append(line(310, 180, 326, 180, LINE, 2, arrow=True))
    b.append(line(590, 180, 574, 180, LINE, 2, arrow=True))
    r3 = [["Account", "Open pipeline", "Bookings", "Reads as"],
          ["Acme Corp", "$100,000", "$200,000", "customer with pipeline"],
          ["Borealis Ltd", "$75,000", "$100,000", "customer with pipeline"],
          ["Cyan Systems", "$75,000", "\u2014", "net-new logo"],
          ["Granite Bank", "\u2014", "$55,000", "nothing in pipeline"]]
    fills = [[INK] * 4,
             [INK, INK, INK, FAINT],
             [INK, INK, INK, FAINT],
             [INK, INK, AMBER, AMBER],
             [INK, AMBER, INK, AMBER]]
    weights = [[700] * 4, [400] * 4, [400] * 4,
               [400, 400, 700, 600], [400, 700, 400, 600]]
    b.append(table(130, 258, [150, 140, 130, 220], r3, row_h=30,
                   fills=fills, weights=weights, where="p4 joined"))
    b.append(rect(130, 420, 640, 74, fill=GREEN_BG, stroke=GREEN, sw=1.5))
    b.append(txt(450, 446, "The join type is the whole point.", 14, 700, GREEN_DK))
    b.append(txt(450, 470, "An inner join would drop the last two rows \u2014 and those "
                           "are the interesting ones.", 13, 400, GREEN_TX))
    b.append(footnote(W, 528, "Because each fact was aggregated before the join, there "
                              "is no Cartesian blow-up:"))
    b.append(footnote(W, 552, "bookings still total $600,000 and open pipeline still "
                              "totals $250,000."))
    svg("part-4-01-conformed-drill-across.svg", W, H,
        "Drill-across with a full outer join",
        "Each fact is aggregated separately at its own grain, then the two summaries are "
        "combined with a full outer join on the conformed Account key. The full outer join "
        "is what preserves accounts present in only one fact, which are exactly the "
        "whitespace rows.",
        "".join(b))


def part4_allocation():
    W, H = 880, 500
    b = [heading(W, "Attribution: splitting one $100,000 deal across three products",
                 "The bridge is where you encode the allocation factor")]
    rows = [["Product", "Line amount", "Equal split", "By line amount", "All-or-nothing"],
            ["Widget", "$40,000", "$33,333", "$40,000  (0.40)", "$100,000"],
            ["Platform License", "$35,000", "$33,333", "$35,000  (0.35)", "$100,000"],
            ["Support Plan", "$25,000", "$33,333", "$25,000  (0.25)", "$100,000"],
            ["Total", "$100,000", "$100,000", "$100,000  (1.00)", "$300,000"]]
    fills = [[INK] * 5,
             [INK, INK, AMBER, GREEN_DK, RED],
             [INK, INK, AMBER, GREEN_DK, RED],
             [INK, INK, AMBER, GREEN_DK, RED],
             [INK, INK, AMBER, GREEN_DK, RED]]
    weights = [[700] * 5, [400] * 5, [400] * 5, [400] * 5, [700] * 5]
    b.append(table(45, 100, [165, 130, 130, 200, 150], rows, row_h=32,
                   fills=fills, weights=weights, where="p4 alloc"))
    cards = [(45, 282, AMBER_BG, AMBER, "Equal split",
              "Simple, and usually wrong.", "Ignores that the products differ."),
             (350, 282, GREEN_BG, GREEN, "By line amount",
              "Usually right. Factors sum", "to 1.00, so revenue reconciles."),
             (655, 282, RED_BG, RED, "All-or-nothing",
              "Fine for \u201cwhich products", "appear\u201d. Triple counts revenue.")]
    for x, y, bg, st, title, l1, l2 in cards:
        b.append(rect(x, y, 180, 100, fill=bg, stroke=st, sw=1.5))
        b.append(txt(x + 90, y + 28, title, 14, 700, st))
        b.append(txt(x + 90, y + 54, l1, 11.5, 400, MUTED))
        b.append(txt(x + 90, y + 74, l2, 11.5, 400, MUTED))
    b.append(footnote(W, 424, "Skipping this step is how \u201crevenue by product\u201d "
                              "ends up larger than total revenue", 14, INK, 600))
    b.append(footnote(W, 450, "\u2014 a red flag any executive will catch, and a "
                              "trust-killer for the whole model."))
    svg("part-4-02-allocation-factor.svg", W, H,
        "Allocation factors on a bridge table",
        "Three ways to split a one hundred thousand dollar opportunity across its three "
        "products: an equal split, an allocation by line amount whose factors sum to one, "
        "and an all-or-nothing attribution that triple counts the revenue.",
        "".join(b))


def part4_whitespace():
    W, H = 820, 560
    b = [heading(W, "Whitespace is a set difference between two conformed facts",
                 "Questions a single flat table cannot express, because it has no notion "
                 "of \u201cin one but not the other\u201d")]
    ox, oy, cw, ch = 230, 130, 270, 150
    b.append(txt(ox + cw / 2, 112, "Has open opportunities", 13, 700, NAVY))
    b.append(txt(ox + cw + 10 + cw / 2, 112, "No open opportunities", 13, 700, NAVY))
    b.append(txt(150, oy + ch / 2, "Has orders", 13, 700, NAVY))
    b.append(txt(150, oy + ch + ch / 2 + 20, "No orders", 13, 700, NAVY))
    cells = [
        (ox, oy, GREEN_BG, GREEN, "Customer with pipeline",
         ["Acme Corp, Borealis Ltd", "$175,000 open \u00b7 $300,000 booked",
          "Grow and protect"]),
        (ox + cw + 10, oy, AMBER_BG, AMBER, "Bought, nothing open",
         ["Delta, Everest, Fjord, Granite", "$300,000 booked \u00b7 $0 open",
          "Re-engagement list"]),
        (ox, oy + ch + 20, NAVY_SOFT, NAVY, "Net-new logo",
         ["Cyan Systems", "$75,000 open \u00b7 $0 booked",
          "Treat unlike an expansion"]),
        (ox + cw + 10, oy + ch + 20, SLATE_BG, LINE, "No relationship yet",
         ["Helios, Ionic, Juniper", "$0 open \u00b7 $0 booked",
          "Prospects, not whitespace"]),
    ]
    for x, y, bg, st, title, lines in cells:
        b.append(rect(x, y, cw, ch, fill=bg, stroke=st, sw=2))
        tf = st if st != LINE else FAINT
        b.append(txt(x + cw / 2, y + 34, fit("t", title, 15, 700, cw - 24, "p4 ws"),
                     15, 700, tf))
        for i, ln in enumerate(lines):
            b.append(txt(x + cw / 2, y + 66 + i * 24,
                         fit("l", ln, 12, 400, cw - 20, "p4 ws"), 12, 400, MUTED))
    # Re-stroke the payoff cell so it reads as the focus of the matrix.
    b.append(rect(ox + cw + 10, oy, cw, ch, fill="none", stroke=AMBER, sw=3.5))
    b.append(footnote(W, 490, "The upper-right cell is the one leadership asks for: "
                              "customers who bought before", 14, INK, 600))
    b.append(footnote(W, 514, "and have nothing in the pipeline right now. "
                              "It is $300,000 of business at risk,"))
    b.append(footnote(W, 538, "and it exists only because the two facts stayed separate."))
    svg("part-4-03-whitespace-matrix.svg", W, H,
        "The whitespace matrix",
        "A two by two matrix of accounts by whether they have orders and whether they "
        "have open opportunities. The four cells are customers with pipeline, customers "
        "who bought but have nothing open, net-new logos, and prospects with no facts at "
        "all. The bought-but-nothing-open cell is three hundred thousand dollars of "
        "business at risk.",
        "".join(b))


# ===========================================================================
# PART 5
# ===========================================================================

def part5_cost():
    W, H = 860, 530
    b = [heading(W, "Where should a calculation live?",
                 "From cheapest at query time to most expensive")]
    tiers = [
        (100, GREEN, GREEN_BG, "1. Materialize it upstream (ETL)",
         "Row-level and stable: Unit Price \u00d7 Quantity, a cleaned category.",
         "Computed once when the data lands. Nothing beats a column that exists."),
        (232, NAVY, NAVY_SOFT, "2. Define it once as a governed metric",
         "Reused but must stay dynamic: Win Rate, Pipeline Coverage.",
         "One definition shared by every dashboard and the agent."),
        (364, AMBER, AMBER_BG, "3. Compute it ad hoc in a single viz",
         "Genuine one-offs only. Invisible to everything else,",
         "easy to get subtly wrong, impossible to govern."),
    ]
    for y, st, bg, title, l1, l2 in tiers:
        b.append(rect(60, y, 740, 104, fill=bg, stroke=st, sw=2))
        b.append(txt(430, y + 32, fit("t", title, 16, 700, 700, "p5 tier"), 16, 700, st))
        b.append(txt(430, y + 60, fit("a", l1, 13, 400, 710, "p5 tier"), 13, 400, MUTED))
        b.append(txt(430, y + 82, fit("b", l2, 13, 400, 710, "p5 tier"), 13, 400, MUTED))
    b.append(footnote(W, 492, "Doing everything dynamically \u201cfor flexibility\u201d "
                              "is how stable row-level values end up"))
    b.append(footnote(W, 514, "recomputed across millions of rows on every "
                              "dashboard load."))
    svg("part-5-01-calc-cost-hierarchy.svg", W, H,
        "Cost hierarchy for calculated fields",
        "Three places a calculation can live, ordered from cheapest to most expensive at "
        "query time: materialized upstream in ETL, defined once as a governed metric in "
        "the semantic model, or computed ad hoc in a single visualization.",
        "".join(b))


def part5_additivity():
    W, H = 880, 440
    b = [heading(W, "Not every measure can be summed",
                 "Additivity decides which aggregations are even legal")]
    cols = [
        (40, GREEN, GREEN_BG, "Additive", "Amount, Bookings",
         ["Sum across any dimension:", "accounts, products, time.",
          "SUM is always safe."], "SUM", "over everything"),
        (315, AMBER, AMBER_BG, "Semi-additive", "Headcount, Balance",
         ["Sum across accounts, but", "never across time. Use the",
          "last value in the period."], "LAST", "over time"),
        (590, RED, RED_BG, "Non-additive", "Win Rate, Margin %",
         ["Never sum, never average", "the ratios. Recompute from", "the parts."],
         "RECOMPUTE", "from numerator and denominator"),
    ]
    for x, st, bg, title, examples, lines, verb, scope in cols:
        b.append(rect(x, 100, 250, 250, fill=bg, stroke=st, sw=2))
        b.append(txt(x + 125, 132, fit("t", title, 16, 700, 236, "p5 add"), 16, 700, st))
        b.append(txt(x + 125, 160, fit("e", examples, 11.5, 600, 236, "p5 add"),
                     11.5, 600, MUTED))
        for i, ln in enumerate(lines):
            b.append(txt(x + 125, 200 + i * 24, fit("l", ln, 12, 400, 236, "p5 add"),
                         12, 400, MUTED))
        b.append(txt(x + 125, 296, verb, 15, 700, st))
        b.append(txt(x + 125, 322, fit("s", scope, 11.5, 400, 236, "p5 add"),
                     11.5, 400, FAINT))
    b.append(footnote(W, 386, "Summing a semi-additive measure across months is the "
                              "classic way to report four times your real headcount.",
                      14, INK, 600))
    b.append(footnote(W, 412, "In Tableau Next, a ratio expression needs the UserAgg "
                              "aggregation type so the engine does not re-aggregate it."))
    svg("part-5-02-additivity.svg", W, H,
        "Additive, semi-additive and non-additive measures",
        "Three classes of measure. Additive measures such as amount can be summed across "
        "any dimension. Semi-additive measures such as headcount and balance can be summed "
        "across accounts but not across time, where the last value should be used. "
        "Non-additive measures such as ratios must be recomputed from their numerator and "
        "denominator.",
        "".join(b))


# ===========================================================================
# PART 6
# ===========================================================================

def part6_order():
    W, H = 800, 620
    b = [heading(W, "The viz layer has its own order of operations",
                 "Where a filter lands in this sequence changes the answer")]
    steps = [
        ("1", "Dimension filters", "Narrow which rows are considered at all.",
         "Stage = Closed, Region = West", NAVY),
        ("2", "Context", "The fixed frame everything downstream respects.",
         "This is the step that sets your denominator", GREEN),
        ("3", "Aggregation", "Rows roll up to the level of detail of the view.",
         "per account, per month", NAVY),
        ("4", "Aggregate filters", "Applied after the roll-up.",
         "SUM(Amount) > 100k \u2014 unknowable before summing", NAVY),
        ("5", "Table calculations", "Run last, on the already-aggregated result.",
         "running total, percent of total, rank", NAVY),
    ]
    y = 92
    for n, title, desc, example, colour in steps:
        hl = colour == GREEN
        b.append(rect(70, y, 660, 86, fill=GREEN_BG if hl else SLATE_BG,
                      stroke=colour, sw=2 if hl else 1.5))
        b.append(rect(88, y + 22, 42, 42, fill=colour, stroke=colour, rx=21))
        b.append(txt(109, y + 50, n, 18, 700, WHITE))
        b.append(txt(150, y + 34, fit("t", title, 16, 700, 560, "p6 step"),
                     16, 700, colour if hl else INK, anchor="start"))
        b.append(txt(150, y + 56, fit("d", desc, 12.5, 400, 560, "p6 step"),
                     12.5, 400, MUTED, anchor="start"))
        b.append(txt(150, y + 75, fit("e", example, 12, 500, 560, "p6 step"),
                     12, 500, FAINT, anchor="start"))
        if y < 92 + 4 * 100:
            b.append(line(400, y + 86, 400, y + 100, LINE, 2, arrow=True))
        y += 100
    b.append(footnote(W, 604, "Percent-of-total, top-N and every ratio metric take their "
                              "denominator from step 2."))
    svg("part-6-01-order-of-operations.svg", W, H,
        "Viz-layer order of operations",
        "Five ordered steps: dimension filters, then context, then aggregation, then "
        "aggregate filters, then table calculations. Context is highlighted because it is "
        "the step that determines the denominator for percent-of-total, top-N and ratio "
        "metrics.",
        "".join(b))


def part6_win_rates():
    W, H = 860, 540
    b = [heading(W, "One field name, four defensible answers",
                 "Every number below is correct. They answer different questions.")]
    b.append(txt(290, 116, "Denominator: closed only", 13, 700, NAVY))
    b.append(txt(570, 116, "Denominator: all opportunities", 13, 700, NAVY))
    b.append(txt(95, 192, "By value", 13, 700, NAVY))
    b.append(txt(95, 322, "By count", 13, 700, NAVY))
    cells = [
        (170, 132, "40.0%", "$400,000 / $1,000,000", GREEN, GREEN_BG),
        (450, 132, "32.0%", "$400,000 / $1,250,000", NAVY, NAVY_SOFT),
        (170, 262, "50.0%", "4 won / 8 closed", AMBER, AMBER_BG),
        (450, 262, "36.4%", "4 won / 11 total", RED, RED_BG),
    ]
    for x, y, big, small, st, bg in cells:
        b.append(rect(x, y, 240, 110, fill=bg, stroke=st, sw=2))
        b.append(txt(x + 120, y + 52, big, 34, 700, st))
        b.append(txt(x + 120, y + 84, fit("s", small, 12.5, 500, 220, "p6 wr"),
                     12.5, 500, MUTED))
    b.append(rect(130, 396, 600, 96, fill=SLATE_BG, stroke=LINE, sw=1.5))
    b.append(txt(430, 422, "An 18-point spread on a metric everyone calls "
                           "\u201cwin rate\u201d.", 14, 700, INK))
    b.append(txt(430, 446, fit("p", "Publish two named metrics \u2014 Win Rate by Value "
                               "and Win Rate by Count \u2014", 12.5, 400, 576, "p6 wr"),
                 12.5, 400, MUTED))
    b.append(txt(430, 468, "and name one of them the house default.", 12.5, 400, MUTED))
    b.append(footnote(W, 508, "Leave the choice implicit and the argument happens in "
                              "the QBR instead of the model."))
    svg("part-6-02-four-win-rates.svg", W, H,
        "Four defensible win rates from one field name",
        "A two by two grid crossing value-weighted against count-based with a "
        "closed-only against all-opportunities denominator, yielding forty percent, "
        "thirty-two percent, fifty percent and thirty-six point four percent. All four "
        "are correct answers to different questions.",
        "".join(b))


# ===========================================================================
# PART 7
# ===========================================================================

def part7_stack():
    W, H = 860, 580
    b = [heading(W, "What the agent reads, and what it rests on",
                 "Metadata only helps once the model underneath is correct")]
    b.append(rect(90, 96, 680, 74, fill=SLATE_BG, stroke=LINE, sw=2))
    b.append(txt(430, 124, "4. Business preferences and defaults", 15, 700, INK))
    b.append(txt(430, 148, "Default currency and date field, fiscal or calendar year, "
                           "which definition is the house default", 12, 400, MUTED))
    b.append(rect(90, 180, 680, 74, fill=NAVY_SOFT, stroke=NAVY, sw=2))
    b.append(txt(430, 208, "3. Governed metrics \u2014 the agent's vocabulary of answers",
                 15, 700, NAVY))
    b.append(txt(430, 232, "Ask for win rate and get the governed one, not a fresh "
                           "SUM/SUM it improvised", 12, 400, MUTED))
    b.append(rect(90, 264, 680, 74, fill=NAVY_SOFT, stroke=NAVY, sw=2))
    b.append(txt(430, 292, "2. Synonyms and business vocabulary", 15, 700, NAVY))
    b.append(txt(430, 316, "reps, AEs, sellers \u2192 User    \u00b7    bookings \u2192 "
                           "closed-won Order.Amount", 12, 400, MUTED))
    b.append(rect(90, 348, 680, 74, fill=GREEN_BG, stroke=GREEN, sw=2))
    b.append(txt(430, 376, "1. Field and object descriptions", 15, 700, GREEN_DK))
    b.append(txt(430, 400, "\u201cACV: annualized contract value, excludes one-time "
                           "fees\u201d \u2014 the highest-leverage metadata", 12, 400,
                 GREEN_TX))
    b.append(rect(90, 438, 680, 78, fill=NAVY, stroke=NAVY, sw=2))
    b.append(txt(430, 468, "0. A correct model  (Parts 1\u20136)", 17, 700, WHITE))
    b.append(txt(430, 494, "Shape, cardinality, grain, calc placement, context. "
                           "Non-optional.", 12.5, 500, NAVY_TEXT))
    b.append(footnote(W, 552, "Rich descriptions on a broken model just help the agent "
                              "find the wrong answer faster."))
    svg("part-7-01-agent-metadata-stack.svg", W, H,
        "The agent metadata stack",
        "Five layers resting on a correct model. From the bottom: a correct model, then "
        "field and object descriptions, then synonyms and business vocabulary, then "
        "governed metrics as the agent's vocabulary of answers, then business preferences "
        "and defaults.",
        "".join(b))


def part7_overfit():
    W, H = 860, 470
    b = [heading(W, "Standardize without overfitting",
                 "Standardization removes ambiguity. Overfitting removes flexibility.")]
    panels = [
        (30, RED, RED_BG, "Under-specified",
         ["\u201cHow are we doing YTD?\u201d", "The agent guesses.",
          "Calendar says $600,000.", "Fiscal says $480,000.",
          "Wrong for half the org."]),
        (300, GREEN, GREEN_BG, "Standardized",
         ["Default: Fiscal YTD.", "Named sibling: Calendar YTD.",
          "Fiscal calendar parameterized", "per business unit.",
          "Synonyms cover the phrasings."]),
        (570, AMBER, AMBER_BG, "Overfitted",
         ["Only fiscal YTD exists.", "One hardcoded fiscal calendar.",
          "\u201cSince January\u201d falls through.", "The board's calendar-year",
          "question cannot be asked."]),
    ]
    for x, st, bg, title, lines in panels:
        b.append(rect(x, 100, 260, 250, fill=bg, stroke=st, sw=2))
        b.append(txt(x + 130, 132, fit("t", title, 15.5, 700, 244, "p7 of"),
                     15.5, 700, st))
        for i, ln in enumerate(lines):
            b.append(txt(x + 130, 168 + i * 26, fit("l", ln, 12, 400, 244, "p7 of"),
                         12, 400, MUTED))
    b.append(txt(430, 386, "The $120,000 gap between the two answers is one January order.",
                 14, 700, INK))
    b.append(footnote(W, 416, "Set a sensible default, keep the alternative as a named "
                              "first-class metric, and parameterize"))
    b.append(footnote(W, 440, "where the organization genuinely varies. Take all of the "
                              "standardization and none of the brittleness."))
    svg("part-7-02-standardize-without-overfitting.svg", W, H,
        "Standardization versus overfitting",
        "Three panels showing the same year-to-date question handled three ways: "
        "under-specified so the agent guesses between a six hundred thousand dollar "
        "calendar answer and a four hundred and eighty thousand dollar fiscal answer; "
        "standardized with a default plus a named sibling and parameterized fiscal "
        "calendars; and overfitted so only one hardcoded definition can be expressed.",
        "".join(b))


# ===========================================================================

BUILDERS = [
    part1_star, part1_wide_table, part1_scd,
    part2_cardinality, part2_no_op, part2_role_playing, part2_orphans,
    part3_fan_out, part3_chasm,
    part4_drill_across, part4_allocation, part4_whitespace,
    part5_cost, part5_additivity,
    part6_order, part6_win_rates,
    part7_stack, part7_overfit,
]


def main():
    global _current
    print(f"Generating {len(BUILDERS)} diagrams in {HERE}")
    for fn in BUILDERS:
        _current = fn.__name__
        fn()
    if _problems:
        print(f"\n{len(_problems)} text-fit problem(s) \u2014 these would overflow "
              f"their container:\n")
        for p in _problems:
            print("  -", p)
        raise SystemExit(1)
    print("\nAll labels fit their containers.")


if __name__ == "__main__":
    main()
