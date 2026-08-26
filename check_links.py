#!/usr/bin/env python3
"""
Checks that every relative link and image reference in the series resolves to a real file.

A broken link in published writing is the cheapest possible defect to prevent and one of the
most common to ship, especially after a restructure. Run this before publishing.

Run:  python3 check_links.py
"""

import os
import re
import sys
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".claude", ".cursor", ".sf", "node_modules", "__pycache__"}

# [text](target) and ![alt](target)
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

problems = []
checked = 0
files_scanned = 0


def markdown_files():
    for root, dirs, names in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in sorted(names):
            if n.endswith(".md"):
                yield os.path.join(root, n)


for path in markdown_files():
    files_scanned += 1
    rel_dir = os.path.dirname(path)
    with open(path) as fh:
        text = fh.read()
    for target in LINK.findall(text):
        target = target.strip()
        parsed = urlparse(target)
        # Skip absolute URLs, mailto, and pure anchors.
        if parsed.scheme or target.startswith("#") or target.startswith("mailto:"):
            continue
        checked += 1
        # Strip any fragment, then percent-decode (paths here contain %20).
        clean = unquote(parsed.path)
        resolved = os.path.normpath(os.path.join(rel_dir, clean))
        if not os.path.exists(resolved):
            problems.append(f"{os.path.relpath(path, HERE)} -> {target}")

# Every diagram should be referenced by at least one article, and every reference should
# point at a diagram that exists. Orphaned diagrams were the original defect.
diagram_dir = os.path.join(HERE, "diagrams")
on_disk = {f for f in os.listdir(diagram_dir) if f.endswith(".svg")}
referenced = set()
for path in markdown_files():
    with open(path) as fh:
        for target in LINK.findall(fh.read()):
            m = re.search(r"diagrams/([^)\s#]+\.svg)", target)
            if m:
                referenced.add(m.group(1))

orphaned = sorted(on_disk - referenced)
missing = sorted(referenced - on_disk)

print(f"Scanned {files_scanned} markdown files, checked {checked} relative links.")
print(f"Diagrams: {len(on_disk)} on disk, {len(referenced)} referenced.")

if problems:
    print(f"\n{len(problems)} broken link(s):")
    for p in problems:
        print("  -", p)
if orphaned:
    print(f"\n{len(orphaned)} diagram(s) on disk but never referenced:")
    for d in orphaned:
        print("  -", d)
if missing:
    print(f"\n{len(missing)} diagram(s) referenced but not on disk:")
    for d in missing:
        print("  -", d)

if problems or orphaned or missing:
    sys.exit(1)
print("\nAll links resolve and every diagram is referenced exactly where it should be.")
