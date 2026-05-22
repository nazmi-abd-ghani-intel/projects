#!/usr/bin/env python3
"""
QDF validation parser for Flame workflows.

Compares QDF attribute values against expected values from a LineItem attributes
report CSV and emits deterministic JSON/CSV summaries plus heatmap artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass
class AttributeExpectation:
    name: str
    raw_expected_text: str = ""
    expected_values: Set[str] = field(default_factory=set)
    used_in_dies: Set[str] = field(default_factory=set)
    used_in_files: Set[str] = field(default_factory=set)
    accepts_any_value: bool = False
    numeric_derived: bool = False


@dataclass
class QdfSummary:
    qdf_name: str
    liid: str = ""
    total_attributes: int = 0
    valid_attributes: int = 0
    invalid_attributes: int = 0
    skipped_attributes: int = 0
    undocumented_attributes: int = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class HeatmapRow:
    qdf: str
    attribute: str
    status: str
    status_code: int
    actual_value: str
    expected_values: str
    issue: str


STATUS_CODE = {
    "VALID": 0,
    "INVALID": 1,
    "SKIPPED": 2,
    "MISSING": 3,
    "ERROR": 4,
    "UNDOCUMENTED": 5,
    "NUMERIC_DERIVED": 6,
}

WORKBOOK_STATUS_ORDER = ["VALID", "INVALID", "SKIPPED", "NUMERIC_DERIVED", "MISSING", "ERROR", "UNDOCUMENTED"]
WORKBOOK_STATUS_STYLE = {
    "VALID": 4,
    "INVALID": 6,
    "SKIPPED": 5,
    "NUMERIC_DERIVED": 8,
    "MISSING": 3,
    "ERROR": 7,
    "UNDOCUMENTED": 6,
}
WORKBOOK_LEGEND = [
    ("VALID", "QDF value matches expected values from LineItem/Fuse.Set source"),
    ("INVALID", "QDF value does NOT match expected values (needs attention!)"),
    ("SKIPPED", "No expected values documented or value is dynamic/pass-through"),
    ("NUMERIC_DERIVED", "Attribute value is consumed by numeric conversion/equation logic"),
    ("MISSING", "Attribute not present in QDF"),
    ("ERROR", "Error loading QDF data"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate QDF JSON data against LineItem report CSV")
    parser.add_argument("--lineitem-report", help="Path to LineItemAttributes report CSV")
    parser.add_argument("--qdf-dir", help="Directory containing QDF JSON files")
    parser.add_argument("--qdf-glob", default="*.json", help="Glob for QDF files (default: *.json)")
    parser.add_argument("--compat-mode", choices=["ffr"], help="Enable compatibility defaults for FFR-style input/output paths")
    parser.add_argument("--output-json", help="Output JSON report path")
    parser.add_argument("--output-csv", help="Output CSV summary path")
    parser.add_argument("--output-heatmap-json", help="Output JSON heatmap path")
    parser.add_argument("--output-heatmap-csv", help="Output CSV heatmap path")
    parser.add_argument("--output-heatmap-xlsx", help="Output XLSX heatmap workbook path")
    parser.add_argument(
        "--strict-undocumented",
        action="store_true",
        help="Treat undocumented QDF attributes as invalid instead of informational",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Promote warning-like mismatches to invalid",
    )
    return parser.parse_args()

def apply_compat_mode_defaults(args: argparse.Namespace) -> argparse.Namespace:
    if args.compat_mode == "ffr":
        if not args.lineitem_report:
            args.lineitem_report = "out/ffr/lineitem_attributes_from_ffr.csv"
        if not args.qdf_dir:
            args.qdf_dir = "out/ffr/qdf-json"
        if not args.output_csv:
            args.output_csv = "out/ffr/qdf_validation_from_ffr.csv"
        if not args.output_json:
            args.output_json = "out/ffr/qdf_validation_from_ffr.json"
        if not args.output_heatmap_csv:
            args.output_heatmap_csv = "out/ffr/qdf_validation_heatmap.csv"
        if not args.output_heatmap_json:
            args.output_heatmap_json = "out/ffr/qdf_validation_heatmap.json"
        if not args.output_heatmap_xlsx:
            args.output_heatmap_xlsx = "out/ffr/QDF_LIRA_Validation_Heatmap.xlsx"

    if not args.lineitem_report:
        raise SystemExit("--lineitem-report is required (or use --compat-mode ffr)")
    if not args.qdf_dir:
        raise SystemExit("--qdf-dir is required (or use --compat-mode ffr)")

    return args


def parse_multi_value_field(raw: str) -> Set[str]:
    if not raw:
        return set()
    return {part.strip() for part in raw.split(";") if part.strip()}


def load_expectations(csv_path: Path) -> Dict[str, AttributeExpectation]:
    if not csv_path.exists():
        raise FileNotFoundError(f"LineItem report not found: {csv_path}")

    expectations: Dict[str, AttributeExpectation] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            attr_name = (row.get("Attribute Name") or "").strip()
            if not attr_name:
                continue

            raw_expected = (row.get("Expected Values") or "").strip()
            expected_values = parse_multi_value_field(raw_expected)
            used_in_dies = parse_multi_value_field((row.get("Used In Dies") or row.get("Used In Modules/Dies") or "").strip())
            used_in_files = parse_multi_value_field((row.get("Used In Files") or "").strip())
            notes = (row.get("Notes") or "").strip()

            expectations[attr_name] = AttributeExpectation(
                name=attr_name,
                raw_expected_text=raw_expected,
                expected_values=expected_values,
                used_in_dies=used_in_dies,
                used_in_files=used_in_files,
                accepts_any_value=("Accepts any other value" in notes) or ("<any-other-value>" in expected_values),
                numeric_derived=("NUMERIC_DERIVED" in notes) or ("Calculated:" in notes),
            )
    return expectations


def is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


def is_validation_rule(value: str) -> bool:
    if not value:
        return False
    return value.startswith("==") or value.startswith("!=") or value.startswith(">=") or value.startswith("<=") or value.startswith("!") or value.startswith(">") or value.startswith("<")


def evaluate_rule(actual: str, rule: str) -> bool:
    if not is_validation_rule(rule):
        return False

    if rule.startswith("!="):
        return actual != rule[2:]
    if rule.startswith("=="):
        return actual == rule[2:]
    if rule.startswith("!"):
        return actual != rule[1:]

    try:
        actual_num = float(actual)
    except Exception:
        return False

    def parse_num(rest: str):
        try:
            return float(rest)
        except Exception:
            return None

    if rule.startswith(">="):
        rhs = parse_num(rule[2:])
        return rhs is not None and actual_num >= rhs
    if rule.startswith("<="):
        rhs = parse_num(rule[2:])
        return rhs is not None and actual_num <= rhs
    if rule.startswith(">"):
        rhs = parse_num(rule[1:])
        return rhs is not None and actual_num > rhs
    if rule.startswith("<"):
        rhs = parse_num(rule[1:])
        return rhs is not None and actual_num < rhs
    return False


def expected_preview(exp: AttributeExpectation) -> str:
    if exp.raw_expected_text:
        return exp.raw_expected_text
    return "; ".join(sorted(exp.expected_values))


def value_matches(actual: str, expectation: AttributeExpectation) -> bool:
    if expectation.raw_expected_text and actual == expectation.raw_expected_text:
        return True

    for expected in expectation.expected_values:
        if actual == expected:
            return True
        if evaluate_rule(actual, expected):
            return True
    return False


def iter_qdf_files(qdf_dir: Path, qdf_glob: str) -> Iterable[Path]:
    for file_path in sorted(qdf_dir.glob(qdf_glob)):
        if file_path.is_file():
            yield file_path
def flatten_attribute_items(items: object) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    if not isinstance(items, list):
        return attrs

    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("attributeName") or item.get("name") or item.get("key")
        if not name:
            continue
        value = item.get("attributeValue")
        if value is None:
            value = item.get("value")
        attrs[str(name)] = "" if value is None else str(value)

    return attrs


def load_qdf_document(qdf_file: Path) -> Tuple[Dict[str, str], str]:
    data = json.loads(qdf_file.read_text(encoding="utf-8"))
    liid = ""
    if isinstance(data, dict):
        for key in ("LIID", "liid", "LineItemId", "lineItemId"):
            value = data.get(key)
            if value is not None:
                liid = str(value)
                break

        for key in ("MarketingAttributes", "marketingAttributes", "attributes"):
            if key in data and isinstance(data[key], dict):
                return {str(k): str(v) for k, v in data[key].items()}, liid

        flattened = flatten_attribute_items(data.get("attributes"))
        if flattened:
            return flattened, liid

        collections = data.get("collections")
        if isinstance(collections, list):
            attrs: Dict[str, str] = {}
            for collection in collections:
                if not isinstance(collection, dict):
                    continue
                attrs.update(flatten_attribute_items(collection.get("attributes")))
            if attrs:
                return attrs, liid

        attrs = {}
        for key, value in data.items():
            if key in {"LIID", "liid", "LineItemId", "lineItemId"}:
                continue
            if isinstance(value, (str, int, float, bool)):
                attrs[str(key)] = str(value)
        return attrs, liid

    raise ValueError(f"Unsupported JSON shape in {qdf_file}")


def validate_qdf(
    qdf_name: str,
    liid: str,
    attrs: Dict[str, str],
    expectations: Dict[str, AttributeExpectation],
    strict_undocumented: bool,
    strict_warnings: bool,
) -> Tuple[QdfSummary, List[HeatmapRow]]:
    summary = QdfSummary(qdf_name=qdf_name, liid=liid)
    rows: List[HeatmapRow] = []

    for attr_name in sorted(attrs):
        attr_value = attrs[attr_name]
        summary.total_attributes += 1

        if attr_name not in expectations:
            summary.undocumented_attributes += 1
            issue = f"{attr_name}='{attr_value}' undocumented"
            if strict_undocumented:
                summary.invalid_attributes += 1
                summary.issues.append(issue)
                status = "INVALID"
            else:
                status = "UNDOCUMENTED"
            rows.append(
                HeatmapRow(
                    qdf=qdf_name,
                    attribute=attr_name,
                    status=status,
                    status_code=STATUS_CODE[status],
                    actual_value=attr_value,
                    expected_values="",
                    issue=issue,
                )
            )
            continue

        exp = expectations[attr_name]
        exp_values = expected_preview(exp)

        if exp.accepts_any_value:
            summary.valid_attributes += 1
            rows.append(
                HeatmapRow(
                    qdf=qdf_name,
                    attribute=attr_name,
                    status="VALID",
                    status_code=STATUS_CODE["VALID"],
                    actual_value=attr_value,
                    expected_values=exp_values,
                    issue="",
                )
            )
            continue

        if not exp.raw_expected_text and not exp.expected_values:
            if attr_value == "":
                summary.valid_attributes += 1
                rows.append(
                    HeatmapRow(
                        qdf=qdf_name,
                        attribute=attr_name,
                        status="VALID",
                        status_code=STATUS_CODE["VALID"],
                        actual_value=attr_value,
                        expected_values="",
                        issue="",
                    )
                )
            else:
                if exp.numeric_derived or is_numeric(attr_value):
                    issue = f"{attr_name} consumed as numeric-derived value"
                    rows.append(
                        HeatmapRow(
                            qdf=qdf_name,
                            attribute=attr_name,
                            status="NUMERIC_DERIVED",
                            status_code=STATUS_CODE["NUMERIC_DERIVED"],
                            actual_value=attr_value,
                            expected_values="",
                            issue=issue,
                        )
                    )
                else:
                    summary.skipped_attributes += 1
                    issue = f"{attr_name} has no expected values in report"
                    rows.append(
                        HeatmapRow(
                            qdf=qdf_name,
                            attribute=attr_name,
                            status="SKIPPED",
                            status_code=STATUS_CODE["SKIPPED"],
                            actual_value=attr_value,
                            expected_values="",
                            issue=issue,
                        )
                    )
            continue

        if is_numeric(attr_value) and all((not is_numeric(v) and not is_validation_rule(v)) for v in exp.expected_values):
            issue = f"{attr_name}='{attr_value}' numeric-vs-enum mismatch"
            if strict_warnings:
                summary.invalid_attributes += 1
                summary.issues.append(issue)
                status = "INVALID"
            else:
                summary.skipped_attributes += 1
                status = "SKIPPED"

            rows.append(
                HeatmapRow(
                    qdf=qdf_name,
                    attribute=attr_name,
                    status=status,
                    status_code=STATUS_CODE[status],
                    actual_value=attr_value,
                    expected_values=exp_values,
                    issue=issue,
                )
            )
            continue

        if value_matches(attr_value, exp):
            summary.valid_attributes += 1
            rows.append(
                HeatmapRow(
                    qdf=qdf_name,
                    attribute=attr_name,
                    status="VALID",
                    status_code=STATUS_CODE["VALID"],
                    actual_value=attr_value,
                    expected_values=exp_values,
                    issue="",
                )
            )
        else:
            summary.invalid_attributes += 1
            issue = f"{attr_name}='{attr_value}' expected one of [{exp_values}]"
            summary.issues.append(issue)
            rows.append(
                HeatmapRow(
                    qdf=qdf_name,
                    attribute=attr_name,
                    status="INVALID",
                    status_code=STATUS_CODE["INVALID"],
                    actual_value=attr_value,
                    expected_values=exp_values,
                    issue=issue,
                )
            )

    for attr_name in sorted(expectations):
        if attr_name in attrs:
            continue
        exp = expectations[attr_name]
        rows.append(
            HeatmapRow(
                qdf=qdf_name,
                attribute=attr_name,
                status="MISSING",
                status_code=STATUS_CODE["MISSING"],
                actual_value="",
                expected_values=expected_preview(exp),
                issue=f"{attr_name} missing in QDF",
            )
        )

    return summary, rows


def write_summary_csv(path: Path, summaries: List[QdfSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "QDF",
            "LIID",
            "Total",
            "Valid",
            "Invalid",
            "Skipped",
            "Undocumented",
            "Issue Count",
        ])
        for summary in summaries:
            writer.writerow([
                summary.qdf_name,
                summary.liid,
                summary.total_attributes,
                summary.valid_attributes,
                summary.invalid_attributes,
                summary.skipped_attributes,
                summary.undocumented_attributes,
                len(summary.issues),
            ])


def write_heatmap_csv(path: Path, rows: List[HeatmapRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "qdf",
            "attribute",
            "status",
            "status_code",
            "actual_value",
            "expected_values",
            "issue",
        ])
        for row in rows:
            writer.writerow([
                row.qdf,
                row.attribute,
                row.status,
                row.status_code,
                row.actual_value,
                row.expected_values,
                row.issue,
            ])


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_heatmap_matrix(rows: List[HeatmapRow]) -> Tuple[List[str], List[str], Dict[str, Dict[str, str]]]:
    qdfs = sorted({row.qdf for row in rows})
    attributes = sorted({row.attribute for row in rows})
    matrix: Dict[str, Dict[str, str]] = {attribute: {qdf: "MISSING" for qdf in qdfs} for attribute in attributes}

    for row in rows:
        matrix[row.attribute][row.qdf] = row.status

    return qdfs, attributes, matrix


def column_name(index: int) -> str:
    result = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def inline_string_cell(ref: str, value: str, style: int = 0) -> str:
    text = escape(value)
    preserve = ' xml:space="preserve"' if value != value.strip() else ""
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t{preserve}>{text}</t></is></c>'


def numeric_cell(ref: str, value: int | float, style: int = 0) -> str:
    return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'


def build_sheet_xml(
    rows: List[List[str]],
    styles: List[List[int]],
    col_widths: List[float] | None = None,
    freeze_pane: str | None = None,
    auto_filter_ref: str | None = None,
    merge_ref: str | None = None,
) -> str:
    max_row = len(rows)
    max_col = max((len(row) for row in rows), default=1)
    dim = f"A1:{column_name(max_col)}{max_row}"

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        f'<dimension ref="{dim}"/>',
        '<sheetViews><sheetView workbookViewId="0">',
    ]
    if freeze_pane:
        parts.append(f'<pane xSplit="1" ySplit="1" topLeftCell="{freeze_pane}" state="frozen" activePane="bottomRight"/>')
    parts.append('</sheetView></sheetViews>')
    parts.append('<sheetFormatPr defaultRowHeight="15"/>')

    if col_widths:
        parts.append('<cols>')
        for idx, width in enumerate(col_widths, start=1):
            parts.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
        parts.append('</cols>')

    parts.append('<sheetData>')
    for row_idx, row in enumerate(rows, start=1):
        parts.append(f'<row r="{row_idx}">')
        row_styles = styles[row_idx - 1] if row_idx - 1 < len(styles) else []
        for col_idx, value in enumerate(row, start=1):
            style = row_styles[col_idx - 1] if col_idx - 1 < len(row_styles) else 0
            ref = f'{column_name(col_idx)}{row_idx}'
            if isinstance(value, (int, float)):
                parts.append(numeric_cell(ref, value, style))
            else:
                parts.append(inline_string_cell(ref, str(value), style))
        parts.append('</row>')
    parts.append('</sheetData>')

    if auto_filter_ref:
        parts.append(f'<autoFilter ref="{auto_filter_ref}"/>')
    if merge_ref:
        parts.append(f'<mergeCells count="1"><mergeCell ref="{merge_ref}"/></mergeCells>')

    parts.append('</worksheet>')
    return ''.join(parts)


def styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="14"/><name val="Calibri"/></font>
  </fonts>
  <fills count="8">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFADD8E6"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD3D3D3"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF90EE90"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFFFE0"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF08080"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFA500"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="9">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="5" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="6" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="7" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def workbook_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="QDF Validation Heatmap" sheetId="1" r:id="rId1"/>
    <sheet name="Legend" sheetId="2" r:id="rId2"/>
    <sheet name="Summary" sheetId="3" r:id="rId3"/>
  </sheets>
</workbook>'''


def workbook_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def root_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''


def content_types_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''


def write_heatmap_workbook(path: Path, rows: List[HeatmapRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    qdfs, attributes, matrix = build_heatmap_matrix(rows)

    heatmap_rows: List[List[str]] = [["LIRA Attribute", *qdfs]]
    heatmap_styles: List[List[int]] = [[2] * (len(qdfs) + 1)]
    for attribute in attributes:
        row_values = [attribute]
        row_styles = [0]
        for qdf in qdfs:
            status = matrix[attribute][qdf]
            row_values.append(status)
            row_styles.append(WORKBOOK_STATUS_STYLE.get(status, 0))
        heatmap_rows.append(row_values)
        heatmap_styles.append(row_styles)

    legend_rows: List[List[str]] = [["Status", "Meaning", "Color"]]
    legend_styles: List[List[int]] = [[2, 2, 2]]
    for status, meaning in WORKBOOK_LEGEND:
        legend_rows.append([status, meaning, status])
        legend_styles.append([0, 0, WORKBOOK_STATUS_STYLE.get(status, 0)])

    total_cells = len(qdfs) * len(attributes)
    counts = {status: 0 for status in WORKBOOK_STATUS_ORDER}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1

    summary_rows: List[List[str | int]] = [
        ["QDF-LIRA Validation Summary", "", ""],
        ["", "", ""],
        ["Total QDFs:", len(qdfs), ""],
        ["Total Attributes:", len(attributes), ""],
        ["Total Cells:", total_cells, ""],
        ["", "", ""],
        ["Status", "Count", "Percentage"],
    ]
    summary_styles: List[List[int]] = [
        [8, 0, 0],
        [0, 0, 0],
        [1, 0, 0],
        [1, 0, 0],
        [1, 0, 0],
        [0, 0, 0],
        [2, 2, 2],
    ]

    ordered_statuses = [status for status in WORKBOOK_STATUS_ORDER if counts.get(status, 0) > 0 or status in {"VALID", "INVALID", "SKIPPED", "MISSING", "ERROR"}]
    for status in ordered_statuses:
        count = counts.get(status, 0)
        percentage = f"{(count / total_cells * 100):.1f}%" if total_cells else "0.0%"
        summary_rows.append([status, count, percentage])
        summary_styles.append([WORKBOOK_STATUS_STYLE.get(status, 0), 0, 0])

    heatmap_xml = build_sheet_xml(
        rows=heatmap_rows,
        styles=heatmap_styles,
        col_widths=[32.0] + [12.0] * len(qdfs),
        freeze_pane="B2",
        auto_filter_ref=f"A1:{column_name(len(qdfs) + 1)}{len(attributes) + 1}",
    )
    legend_xml = build_sheet_xml(rows=legend_rows, styles=legend_styles, col_widths=[18.0, 60.0, 14.0])
    summary_xml = build_sheet_xml(rows=summary_rows, styles=summary_styles, col_widths=[24.0, 12.0, 12.0], merge_ref="A1:C1")

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        zf.writestr("xl/styles.xml", styles_xml())
        zf.writestr("xl/worksheets/sheet1.xml", heatmap_xml)
        zf.writestr("xl/worksheets/sheet2.xml", legend_xml)
        zf.writestr("xl/worksheets/sheet3.xml", summary_xml)


def default_heatmap_paths(args: argparse.Namespace) -> Tuple[Path | None, Path | None, Path | None]:
    csv_out = Path(args.output_heatmap_csv).resolve() if args.output_heatmap_csv else None
    json_out = Path(args.output_heatmap_json).resolve() if args.output_heatmap_json else None
    xlsx_out = Path(args.output_heatmap_xlsx).resolve() if args.output_heatmap_xlsx else None

    if csv_out or json_out or xlsx_out:
        return csv_out, json_out, xlsx_out

    if args.output_json or args.output_csv:
        anchor = Path(args.output_json).resolve() if args.output_json else Path(args.output_csv).resolve()
        out_dir = anchor.parent
        workbook_dir = out_dir.parent if out_dir.name.lower() == "ffr" else out_dir
        return out_dir / "qdf_validation_heatmap.csv", out_dir / "qdf_validation_heatmap.json", workbook_dir / "QDF_LIRA_Validation_Heatmap.xlsx"

    return None, None, None


def main() -> int:
    args = apply_compat_mode_defaults(parse_args())
    lineitem_report = Path(args.lineitem_report).resolve()
    qdf_dir = Path(args.qdf_dir).resolve()

    if not qdf_dir.exists() or not qdf_dir.is_dir():
        raise SystemExit(f"QDF directory not found: {qdf_dir}")

    expectations = load_expectations(lineitem_report)
    summaries: List[QdfSummary] = []
    heatmap_rows: List[HeatmapRow] = []

    for qdf_file in iter_qdf_files(qdf_dir, args.qdf_glob):
        qdf_name = qdf_file.stem
        attrs, liid = load_qdf_document(qdf_file)
        summary, rows = validate_qdf(
            qdf_name,
            liid,
            attrs,
            expectations,
            strict_undocumented=args.strict_undocumented,
            strict_warnings=args.strict_warnings,
        )
        summaries.append(summary)
        heatmap_rows.extend(rows)

    total_qdfs = len(summaries)
    with_invalid = sum(1 for summary in summaries if summary.invalid_attributes > 0)

    payload = {
        "lineitem_report": str(lineitem_report),
        "qdf_dir": str(qdf_dir),
        "qdf_count": total_qdfs,
        "qdfs_with_invalid": with_invalid,
        "summary": [
            {
                "qdf": summary.qdf_name,
                "liid": summary.liid,
                "total": summary.total_attributes,
                "valid": summary.valid_attributes,
                "invalid": summary.invalid_attributes,
                "skipped": summary.skipped_attributes,
                "undocumented": summary.undocumented_attributes,
                "issues": summary.issues,
            }
            for summary in summaries
        ],
    }

    heatmap_payload = {
        "lineitem_report": str(lineitem_report),
        "qdf_dir": str(qdf_dir),
        "qdf_count": total_qdfs,
        "rows": [
            {
                "qdf": row.qdf,
                "attribute": row.attribute,
                "status": row.status,
                "status_code": row.status_code,
                "actual_value": row.actual_value,
                "expected_values": row.expected_values,
                "issue": row.issue,
            }
            for row in heatmap_rows
        ],
    }

    if args.output_json:
        write_json(Path(args.output_json), payload)
    if args.output_csv:
        write_summary_csv(Path(args.output_csv), summaries)

    heatmap_csv_out, heatmap_json_out, heatmap_xlsx_out = default_heatmap_paths(args)
    if heatmap_csv_out:
        write_heatmap_csv(heatmap_csv_out, heatmap_rows)
    if heatmap_json_out:
        write_json(heatmap_json_out, heatmap_payload)
    if heatmap_xlsx_out:
        write_heatmap_workbook(heatmap_xlsx_out, heatmap_rows)

    print(
        json.dumps(
            {
                "qdf_count": total_qdfs,
                "qdfs_with_invalid": with_invalid,
                "heatmap_rows": len(heatmap_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



