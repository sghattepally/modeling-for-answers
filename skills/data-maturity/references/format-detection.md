# Format Detection

`assess_sdm.py` and `batch_assess.py` auto-detect format per file — a customer can hand you a
folder with any mix of these and every file gets routed to the right parser.

## Detection rules (in order)

1. **Extension `.tds` or `.tdsx`** → classic Tableau published data source.
   - `.tdsx` is a zip; the parser opens it and reads the first `*.tds` entry found inside.
   - `.tds` is plain XML at the root — no zip unwrap needed.
   - See `scripts/lib/parse_tds.py`.
2. **Everything else** → try JSON first, then YAML.
   - `json.loads()` is attempted first. If it parses to a `dict`, treat as Tableau Next SDM JSON
     (`scripts/lib/parse_sdm_json.py`, `fmt="sdm-json"`).
   - If JSON parsing fails, fall back to `yaml.safe_load()`. Valid JSON is already valid YAML, so
     this fallback only fires for actual YAML syntax (unquoted keys, `---` documents, etc.) or for
     files with a `.yaml`/`.yml` extension. Same parser (`parse_sdm_json`), `fmt="yaml"` — the key
     shape is identical, only the serialization differs.
   - If neither parses, or the result isn't a dict, the file is skipped (single-file mode: raises;
     batch mode: recorded as skipped with the error, batch continues).

## Why one parser handles both JSON and YAML

A hand-authored SDM spec (a customer describing their model before it's built, or exporting from
some other tool) uses the same key names as the live Tableau Next API response
(`semanticDataObjects`, `calculatedMeasurements`, `semanticMetrics`, etc.) — see
`~/.claude/skills/tableau-semantic-authoring/references/api-reference.md` for the canonical shape.
YAML and JSON are just two serializations of the same tree, so `parse_sdm_json.py` accepts a plain
Python dict regardless of which file format it came from.

## Field-name tolerance

Real-world exports vary slightly in key names (an artifact of API version drift and hand-authored
specs copying an older shape). The parser tries multiple keys where this is known to happen:

| Concept | Keys tried, in order |
|---|---|
| Calculated dimensions | `calculatedDimensions`, `semanticCalculatedDimensions` |
| Calculated measurements | `calculatedMeasurements`, `semanticCalculatedMeasurements` |
| Synonyms | `synonyms`, `aliases` |
| Business preferences | `businessPreferences`, `defaults` |
| Currency default | `currency`, `defaultCurrency` |
| Fiscal year start | `fiscalYearStart`, `fiscal_year_start` |

If a supplied file uses a key shape not listed here, the corresponding section will be empty
rather than raising — check `parse_warnings` in the JSON output (`--json` flag) for a note when a
top-level `semanticDataObjects` array wasn't found at all, which is the strongest signal the file
isn't in the expected shape.

## Adding a new format later

The normalized model (`scripts/lib/normalize.py`) is the seam: any new parser just needs to
produce a `NormModel` with the same fields. Power BI `.bim` or a dbt semantic-layer YAML could be
added as `scripts/lib/parse_bim.py` / `parse_dbt.py` without touching `score.py` at all — this is
called out as future scope in the skill's plan, not built yet.
