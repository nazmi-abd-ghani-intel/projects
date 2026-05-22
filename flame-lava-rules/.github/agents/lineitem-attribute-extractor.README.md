# LineItem Attribute Extractor README

## Agent File
- [.github/agents/lineitem-attribute-extractor.agent.md](.github/agents/lineitem-attribute-extractor.agent.md)

## Script Engine
- [scripts/lineitem_attribute_parser.py](scripts/lineitem_attribute_parser.py)

## Purpose
Extract and document LineItem attribute usage from Flame Fuse.Set C# code, including expected values, condition patterns, and module/file usage, with evidence-backed reporting.

## Supported Inputs
- Repository path
- Repository URL
- GitHub tree URL (`.../tree/<branch-or-tag>`)
- Optional branch/tag/commit
- Optional `mode=auto|script|agent`
- Optional output path (must remain under user workdir)

## Execution Modes
- `auto`: run parser script first, then fill gaps via agent analysis.
- `script`: parser-only deterministic extraction.
- `agent`: direct analysis without script execution.

## What It Extracts
- Attribute references from `lineItem.<ATTRIBUTE>.Value` and `.IsDefined`
- Expected values from equality/inequality
- Null checks
- Contains-based logic
- Identifier/constant comparisons
- Numeric comparison rules (`>`, `>=`, `<`, `<=`, `!`)
- Switch/case/default semantics
- Module/file usage footprint
- Optional LIRA validity status

## Corner Cases Covered
- Excludes commented-out code and exception-message-only string interpolation
- Handles multi-line and switch-heavy logic
- Captures default-branch any-value semantics
- Preserves symbolic comparison context when literal resolution is not possible

## Output Contract
Report order:
1. Input Resolution
2. Script Reference Mapping
3. Attribute Inventory Summary
4. Attribute Table
5. LIRA Validation
6. Calculation and Logic Notes
7. Risks and Gaps
8. Suggested Next Steps

## Workdir Output Rule
All generated artifacts must stay under user working directory, such as:
- `./out/lineitem/lineitem_attribute_report.json`
- `./out/lineitem/lineitem_attribute_report.csv`

## Example Command
```powershell
$outDir = Join-Path $PWD "out\lineitem"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

python scripts/lineitem_attribute_parser.py \
  --repo "." \
  --lira ".\Rules\LineItem.lira" \
  --output-json (Join-Path $outDir "lineitem_attribute_report.json") \
  --output-csv (Join-Path $outDir "lineitem_attribute_report.csv")
```
