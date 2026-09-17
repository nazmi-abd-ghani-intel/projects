<#
.SYNOPSIS
  Builds product-config.json from the human-editable product-config.csv.

.DESCRIPTION
  Product/key-type mappings are maintained in Input\product-config.csv (one row per
  Product/Milestone/Die/Usage/KeyType combination, with an optional Category column).
  This script converts that CSV into Input\product-config.json, grouped per product as:
    product -> {
      usageCategory: { usage: category },   -- only present if this product's rows supplied a Category
      milestones: { milestone -> die -> { keyType: usage } }
    }
  for inventory-dashboard.html to consume for the Product filter. usageCategory is scoped
  per product (not global) because the same usage name can map to a different category for
  a different product, and it is entirely optional — a product with no Category values in
  the CSV simply has no usageCategory key, nothing is hardcoded or defaulted.

  To update the product configuration, edit product-config.csv (e.g. in Excel) and re-run
  this script — no JSON editing required. This script also runs automatically at the end
  of refresh-inventory-dashboard.ps1.

.PARAMETER InputCsv
  Path to the source CSV. Defaults to Input\product-config.csv.

.PARAMETER OutputJson
  Path to write the generated JSON. Defaults to Input\product-config.json.
#>
param(
  [string]$InputCsv = "$PSScriptRoot\Input\product-config.csv",
  [string]$OutputJson = "$PSScriptRoot\Input\product-config.json"
)

if (-not (Test-Path $InputCsv)) {
  throw "Product config CSV not found at $InputCsv"
}

$rows = Import-Csv -Path $InputCsv

# Category is optional; only Product/Milestone/Die/Usage/KeyType are required.
$required = 'Product','Milestone','Die','Usage','KeyType'
$missing = $required | Where-Object { $_ -notin $rows[0].PSObject.Properties.Name }
if ($missing) {
  throw "product-config.csv is missing required column(s): $($missing -join ', ')"
}
$hasCategoryColumn = 'Category' -in $rows[0].PSObject.Properties.Name

$tree = [ordered]@{}
$uniqueKeyTypes = [System.Collections.Generic.HashSet[int]]::new()
$badRows = [System.Collections.Generic.List[string]]::new()
$rowCount = 0
$lineNum = 1
foreach ($r in $rows) {
  $lineNum++
  $keyTypeRaw = ($r.KeyType) -as [string]
  $keyType = 0
  if (-not [int]::TryParse($keyTypeRaw, [ref]$keyType)) {
    $badRows.Add("Line $lineNum : KeyType '$keyTypeRaw' is not a valid integer, skipped")
    continue
  }
  if ([string]::IsNullOrWhiteSpace($r.Product) -or [string]::IsNullOrWhiteSpace($r.Milestone) -or [string]::IsNullOrWhiteSpace($r.Die) -or [string]::IsNullOrWhiteSpace($r.Usage)) {
    $badRows.Add("Line $lineNum : missing Product/Milestone/Die/Usage, skipped")
    continue
  }
  $category = $null
  if ($hasCategoryColumn -and -not [string]::IsNullOrWhiteSpace($r.Category)) {
    $category = $r.Category.Trim()
  }
  $product = $r.Product.Trim()
  $milestone = $r.Milestone.Trim()
  $die = $r.Die.Trim()
  $usage = $r.Usage.Trim()

  if (-not $tree.Contains($product)) {
    $tree[$product] = [ordered]@{
      milestones = [ordered]@{}
    }
  }
  $productNode = $tree[$product]

  if ($null -ne $category) {
    if (-not $productNode.Contains('usageCategory')) { $productNode.Insert(0, 'usageCategory', [ordered]@{}) }
    $usageCategory = $productNode.usageCategory
    if ($usageCategory.Contains($usage) -and $usageCategory[$usage] -ne $category) {
      $badRows.Add("Line $lineNum : usage '$usage' has category '$category' here but '$($usageCategory[$usage])' elsewhere for product '$product'; keeping first value")
    } elseif (-not $usageCategory.Contains($usage)) {
      $usageCategory[$usage] = $category
    }
  }

  $milestones = $productNode.milestones
  if (-not $milestones.Contains($milestone)) { $milestones[$milestone] = [ordered]@{} }
  if (-not $milestones[$milestone].Contains($die)) { $milestones[$milestone][$die] = [ordered]@{} }

  $keyTypeKey = "$keyType"
  if ($milestones[$milestone][$die].Contains($keyTypeKey)) {
    $badRows.Add("Line $lineNum : duplicate KeyType '$keyType' for $product/$milestone/$die, skipped")
    continue
  }
  $milestones[$milestone][$die][$keyTypeKey] = $usage

  [void]$uniqueKeyTypes.Add($keyType)
  $rowCount++
}

if ($badRows.Count -gt 0) {
  Write-Warning "product-config.csv had $($badRows.Count) problem row(s):"
  $badRows | ForEach-Object { Write-Warning "  $_" }
}

$json = $tree | ConvertTo-Json -Depth 6
Set-Content -Path $OutputJson -Value $json -Encoding utf8

Write-Host "Built $OutputJson from $InputCsv"
Write-Host "  Rows: $rowCount | Unique key types: $($uniqueKeyTypes.Count) | Products: $($tree.Keys -join ', ')"
