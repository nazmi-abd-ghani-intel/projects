---
name: volume-forecast-analysis
description: 'Analyze the VolumeForecast Excel workbook and its Power BI semantic-model query. Use for Excel Data-tab extraction, NOVA LAKE or RAZOR LAKE filtering, TEST or FINISH stage filtering, KF_Qty analysis, CSV generation, summaries, validation, and optional DAX query preparation.'
argument-hint: '[question or analysis goal]'
user-invocable: true
disable-model-invocation: false
---

# Volume Forecast Analysis

## Purpose

Use the local Excel workbook as the primary source for analysis. Power BI and DAX are optional references only; do not require Power BI connectivity, REST API access, XMLA access, OneLake access, or a Fabric Lakehouse to analyze the local data.

## Source and outputs

- Default source: `VolumeForecast.xlsx`, sheet `Data`
- Local analysis script: [analyze-volume-forecast.ps1](../../../scripts/analyze-volume-forecast.ps1)
- Primary raw filtered output: `output/volume-forecast-filtered.csv`
- Optional grouped output: `output/volume-forecast-summary.csv`
- Optional DAX: `output/volume-forecast-query.dax`

## Data contract

The `Data` sheet is expected to contain:

`ProductGroupNm`, `DesignItemDsc`, `RevStepCd`, `SpeedDesignId`, `YearQuarterTxt`, `YearMonthTxt`, `MfgLocationCd`, `DesignItemMilestone`, `MfgLocationStage`, `KF_Qty`.

The header may have leading blank rows. The script finds the header by `ProductGroupNm` instead of assuming a fixed row number.

## Current filter profile

- Current product-group filter: `NOVA LAKE`, `RAZOR LAKE`
- Current manufacturing-stage filter: `TEST`, `FINISH`
- These are selectable defaults for the current analysis, not permanent business rules.
- Ask the user for different product groups or stages when the analysis requires another slice.
- Quantity field: `KF_Qty`
- Main grouping: `YearQuarterTxt`, `SpeedDesignId`, `DesignItemMilestone`, `MfgLocationStage`

Do not add a `DesignItemMilestone` filter unless the user explicitly requests one. A blank milestone is a valid value and must not be silently removed.

## Procedure

1. Treat the last saved `VolumeForecast.xlsx` on the `Data` tab as the current source of truth.
2. When fresh source data is required, open the workbook in Excel, select `Data > Refresh All`, wait for completion, and save the workbook. Resolve any Excel credentials or connection errors before continuing.
3. Run the local script from the repository root:

   ```powershell
   .\scripts\analyze-volume-forecast.ps1
   ```

4. Treat `volume-forecast-filtered.csv` as the primary downstream input and inspect it before any summarization.
5. Use `KF_Qty` as numeric quantity. Treat blank or invalid quantities as zero only when documenting that choice.
6. Use the summary CSV only when a quick grouped view is useful; it is optional and must not replace the row-level CSV for detailed analysis.
7. Report row counts, distinct product groups, stages, and total quantity when validating an output.
8. Never overwrite the Excel source file. Generated files belong under `output/`.

## Custom filters

Use script parameters when the user changes the requested products or stages:

```powershell
.\scripts\analyze-volume-forecast.ps1 `
    -ProductGroups 'NOVA LAKE' `
    -Stages 'TEST', 'FINISH'
```

For example, a different selection can be run without changing the script:

```powershell
.\scripts\analyze-volume-forecast.ps1 `
    -ProductGroups 'NOVA LAKE' `
    -Stages 'FINISH'
```

For a different workbook or output location, use `-WorkbookPath` and `-OutputDirectory`.

## Optional Power BI/DAX path

When the user asks for a DAX query, generate or use this equivalent raw-row query:

```DAX
EVALUATE
FILTER(
    'factSnOPdata',
    'factSnOPdata'[ProductGroupNm] IN { "NOVA LAKE", "RAZOR LAKE" }
        && 'factSnOPdata'[MfgLocationStage] IN { "TEST", "FINISH" }
)
ORDER BY
    'factSnOPdata'[YearQuarterTxt],
    'factSnOPdata'[SpeedDesignId],
    'factSnOPdata'[DesignItemMilestone]
```

DAX returns a table; it does not write a CSV by itself. Export DAX results from Power BI Desktop, DAX Studio, or Excel when needed. Do not claim that the DAX result and the Excel CSV are equivalent without comparing row counts and columns.

To refresh the Power BI path, open the PBIP/report in Power BI Desktop, select `Home > Refresh`, and rerun the DAX query. This is independent of Excel `Data > Refresh All`; refreshing Power BI does not update the local workbook, and refreshing Excel does not update the Power BI semantic model.

## Access boundaries

- The local Excel workflow does not need Power BI permissions.
- A thin PBIP report references a remote semantic model and does not contain the underlying data source.
- A Power BI API `403` means the API route is blocked by permissions or tenant policy; do not bypass it or invent credentials.
- Do not infer a Lakehouse, Warehouse, or OneLake table from the PBIP alone.
- If the user asks for live or scheduled Power BI data, explain that it requires separate Power BI Service permissions and automation. Continue using the local Excel workflow when that access is unavailable.