# QDF Validation Specialist README

## Agent File
- [.github/agents/qdf-validation-specialist.agent.md](.github/agents/qdf-validation-specialist.agent.md)

## Script Engine
- [scripts/qdf_validation_parser.py](scripts/qdf_validation_parser.py)

## Purpose
Validate QDF attributes against documented LineItem expectations and produce per-QDF mismatch summaries, invalid/skipped/undocumented breakdowns, and remediation guidance.

## Reference Alignment
Based on behavior in `Rules/QDFValidationTests.cs`, with improvements for robust parsing and deterministic output.

## Supported Inputs
- Repository path
- Repository URL
- GitHub tree URL (`.../tree/<branch-or-tag>`)
- Optional branch/tag/commit
- Optional `mode=auto|script|agent`
- Optional QDF source path and lineitem report path

## Execution Modes
- `auto`: run parser script then apply agent interpretation.
- `script`: deterministic script-only run.
- `agent`: direct analysis path.

## Validation Semantics
- Status classes: `VALID`, `INVALID`, `SKIPPED`, `UNDOCUMENTED`, `ERROR`
- Rule evaluation: `!x`, `>x`, `>=x`, `<x`, `<=x`
- Supports `accepts any value` behavior from report semantics
- Handles numeric-vs-enum warning cases

## Strictness Options
From script:
- `--strict-undocumented`
- `--strict-warnings`

## Output Artifacts
Typical generated artifacts:
- `./out/qdf/qdf_validation_report.json`
- `./out/qdf/qdf_validation_summary.csv`

## Workdir Output Rule
Do not hardcode machine paths. Keep all generated files under current working directory.

## Example Command
```powershell
$outDir = Join-Path $PWD "out\qdf"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

python scripts/qdf_validation_parser.py \
  --lineitem-report ".\Rules\LineItemAttributes_Report.csv" \
  --qdf-dir ".\qdf-json" \
  --output-json (Join-Path $outDir "qdf_validation_report.json") \
  --output-csv (Join-Path $outDir "qdf_validation_summary.csv")
```
