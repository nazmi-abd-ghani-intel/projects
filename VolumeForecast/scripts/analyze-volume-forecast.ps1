param(
    [string]$WorkbookPath = (Join-Path $PSScriptRoot '..\VolumeForecast.xlsx'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\output'),
    [string[]]$ProductGroups = @('NOVA LAKE', 'RAZOR LAKE'),
    [string[]]$Stages = @('TEST', 'FINISH')
)

$ErrorActionPreference = 'Stop'

function Release-ComObject {
    param([object]$Object)

    if ($null -ne $Object -and [System.Runtime.InteropServices.Marshal]::IsComObject($Object)) {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($Object) | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)) {
    throw "Workbook not found: $WorkbookPath"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$excel = $null
$workbook = $null
$worksheet = $null
$usedRange = $null
$records = [System.Collections.Generic.List[object]]::new()
$headerRow = $null
$lastRow = $null
$sourceRecordCount = 0

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Open((Resolve-Path -LiteralPath $WorkbookPath), $null, $true)
    $worksheet = $workbook.Worksheets.Item('Data')
    $usedRange = $worksheet.UsedRange

    $columnMap = @{}
    $firstUsedRow = $usedRange.Row
    $firstUsedColumn = $usedRange.Column
    $lastRow = $firstUsedRow + $usedRange.Rows.Count - 1
    $lastColumn = $firstUsedColumn + $usedRange.Columns.Count - 1
    for ($row = $firstUsedRow; $row -le $lastRow; $row++) {
        $firstValue = [string]$worksheet.Cells($row, $firstUsedColumn).Text
        if ($firstValue -eq 'ProductGroupNm') {
            $headerRow = $row
            for ($column = $firstUsedColumn; $column -le $lastColumn; $column++) {
                $name = [string]$worksheet.Cells($row, $column).Text
                if (-not [string]::IsNullOrWhiteSpace($name)) {
                    $columnMap[$name] = $column
                }
            }
            break
        }
    }

    if ($null -eq $headerRow) {
        throw "Could not find the ProductGroupNm header on the Data sheet."
    }

    $requiredColumns = @(
        'ProductGroupNm', 'DesignItemDsc', 'RevStepCd', 'SpeedDesignId',
        'YearQuarterTxt', 'YearMonthTxt', 'MfgLocationCd',
        'DesignItemMilestone', 'MfgLocationStage', 'KF_Qty'
    )
    $missingColumns = @($requiredColumns | Where-Object { -not $columnMap.ContainsKey($_) })
    if ($missingColumns.Count -gt 0) {
        throw "Missing required columns: $($missingColumns -join ', ')"
    }

    $productLookup = @{}
    foreach ($productGroup in $ProductGroups) {
        $productLookup[$productGroup.Trim().ToUpperInvariant()] = $true
    }
    $stageLookup = @{}
    foreach ($stage in $Stages) {
        $stageLookup[$stage.Trim().ToUpperInvariant()] = $true
    }

    for ($row = $headerRow + 1; $row -le $lastRow; $row++) {
        $productGroup = ([string]$worksheet.Cells($row, $columnMap['ProductGroupNm']).Text).Trim()
        $stage = ([string]$worksheet.Cells($row, $columnMap['MfgLocationStage']).Text).Trim()
        if ([string]::IsNullOrWhiteSpace($productGroup) -or $productGroup -eq 'Grand Total') { continue }
        $sourceRecordCount++
        if (-not $productLookup.ContainsKey($productGroup.ToUpperInvariant())) { continue }
        if (-not $stageLookup.ContainsKey($stage.ToUpperInvariant())) { continue }

        $record = [ordered]@{}
        foreach ($column in $requiredColumns) {
            if ($column -eq 'KF_Qty') {
                continue
            }
            $record[$column] = [string]$worksheet.Cells($row, $columnMap[$column]).Text
        }
        $quantityValue = $worksheet.Cells($row, $columnMap['KF_Qty']).Value2
        $quantity = 0.0
        if ($quantityValue -is [ValueType]) {
            try {
                $quantity = [double]$quantityValue
            }
            catch {
                $quantity = 0.0
            }
        }
        elseif (-not [string]::IsNullOrWhiteSpace([string]$quantityValue)) {
            $parsed = [double]0
            $invariant = [Globalization.CultureInfo]::InvariantCulture
            $current = [Globalization.CultureInfo]::CurrentCulture
            if ([double]::TryParse([string]$quantityValue, [Globalization.NumberStyles]::Any, $invariant, [ref]$parsed) -or
                [double]::TryParse([string]$quantityValue, [Globalization.NumberStyles]::Any, $current, [ref]$parsed)) {
                $quantity = $parsed
            }
        }
        $record['KF_Qty'] = $quantity
        $records.Add([pscustomobject]$record)
    }
}
finally {
    if ($null -ne $workbook) { $workbook.Close($false) }
    if ($null -ne $excel) { $excel.Quit() }
    Release-ComObject $usedRange
    Release-ComObject $worksheet
    Release-ComObject $workbook
    Release-ComObject $excel
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

$rawOutput = Join-Path $OutputDirectory 'volume-forecast-filtered.csv'
$summaryOutput = Join-Path $OutputDirectory 'volume-forecast-summary.csv'
$daxOutput = Join-Path $OutputDirectory 'volume-forecast-query.dax'
$validationOutput = Join-Path $OutputDirectory 'volume-forecast-validation.json'

$records | Export-Csv -LiteralPath $rawOutput -NoTypeInformation -Encoding UTF8

$summary = $records |
    Group-Object YearQuarterTxt, SpeedDesignId, DesignItemMilestone, MfgLocationStage |
    ForEach-Object {
        $first = $_.Group | Select-Object -First 1
        [pscustomobject]@{
            ProductGroupNm = $first.ProductGroupNm
            YearQuarterTxt = $first.YearQuarterTxt
            SpeedDesignId = $first.SpeedDesignId
            DesignItemMilestone = $first.DesignItemMilestone
            MfgLocationStage = $first.MfgLocationStage
            KF_Qty = ($_.Group | Measure-Object -Property KF_Qty -Sum).Sum
        }
    } |
    Sort-Object YearQuarterTxt, SpeedDesignId, DesignItemMilestone, MfgLocationStage

$summary | Export-Csv -LiteralPath $summaryOutput -NoTypeInformation -Encoding UTF8

$validation = [ordered]@{
    SourceWorkbook = (Resolve-Path -LiteralPath $WorkbookPath).Path
    SourceSheet = 'Data'
    SourceDataRows = $sourceRecordCount
    FilteredRows = $records.Count
    ProductGroups = @($ProductGroups)
    Stages = @($Stages)
    TotalKF_Qty = ($records | Measure-Object -Property KF_Qty -Sum).Sum
    GeneratedAt = (Get-Date).ToString('o')
}
$validation | ConvertTo-Json | Set-Content -LiteralPath $validationOutput -Encoding UTF8

$productLiteral = ($ProductGroups | ForEach-Object { '"' + ($_ -replace '"', '""') + '"' }) -join ', '
$stageLiteral = ($Stages | ForEach-Object { '"' + ($_ -replace '"', '""') + '"' }) -join ', '
$dax = @"
EVALUATE
FILTER(
    'factSnOPdata',
    'factSnOPdata'[ProductGroupNm] IN { $productLiteral }
        && 'factSnOPdata'[MfgLocationStage] IN { $stageLiteral }
)
ORDER BY
    'factSnOPdata'[YearQuarterTxt],
    'factSnOPdata'[SpeedDesignId],
    'factSnOPdata'[DesignItemMilestone]
"@
$dax | Set-Content -LiteralPath $daxOutput -Encoding UTF8

Write-Output "Filtered rows: $($records.Count)"
Write-Output "Raw CSV: $rawOutput"
Write-Output "Summary CSV: $summaryOutput"
Write-Output "Optional DAX: $daxOutput"
Write-Output "Validation: $validationOutput"