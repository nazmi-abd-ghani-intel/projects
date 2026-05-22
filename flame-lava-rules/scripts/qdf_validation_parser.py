#!/usr/bin/env python3
"""
QDF validation parser for Flame workflows.

Compares QDF attribute values against expected values from a LineItem attributes
report CSV and emits deterministic JSON/CSV summaries.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set


@dataclass
class AttributeExpectation:
    name: str
    expected_values: Set[str] = field(default_factory=set)
    used_in_dies: Set[str] = field(default_factory=set)
    used_in_files: Set[str] = field(default_factory=set)
    accepts_any_value: bool = False


@dataclass
class QdfSummary:
    qdf_name: str
    total_attributes: int = 0
    valid_attributes: int = 0
    invalid_attributes: int = 0
    skipped_attributes: int = 0
    undocumented_attributes: int = 0
    issues: List[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate QDF JSON data against LineItem report CSV")
    parser.add_argument("--lineitem-report", required=True, help="Path to LineItemAttributes report CSV")
    parser.add_argument("--qdf-dir", required=True, help="Directory containing QDF JSON files")
    parser.add_argument("--qdf-glob", default="*.json", help="Glob for QDF files (default: *.json)")
    parser.add_argument("--output-json", help="Output JSON report path")
    parser.add_argument("--output-csv", help="Output CSV summary path")
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

            expected_values = parse_multi_value_field((row.get("Expected Values") or "").strip())
            used_in_dies = parse_multi_value_field((row.get("Used In Dies") or row.get("Used In Modules/Dies") or "").strip())
            used_in_files = parse_multi_value_field((row.get("Used In Files") or "").strip())
            notes = (row.get("Notes") or "").strip()

            expectations[attr_name] = AttributeExpectation(
                name=attr_name,
                expected_values=expected_values,
                used_in_dies=used_in_dies,
                used_in_files=used_in_files,
                accepts_any_value=("Accepts any other value" in notes) or ("<any-other-value>" in expected_values),
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
    return value.startswith(">=") or value.startswith("<=") or value.startswith("!") or value.startswith(">") or value.startswith("<")


def evaluate_rule(actual: str, rule: str) -> bool:
    if not is_validation_rule(rule):
        return False

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


def value_matches(actual: str, expected: Set[str]) -> bool:
    for exp in expected:
        if actual == exp:
            return True
        if evaluate_rule(actual, exp):
            return True
    return False


def iter_qdf_files(qdf_dir: Path, qdf_glob: str) -> Iterable[Path]:
    for file_path in sorted(qdf_dir.glob(qdf_glob)):
        if file_path.is_file():
            yield file_path


def load_qdf_attributes(qdf_file: Path) -> Dict[str, str]:
    data = json.loads(qdf_file.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # Flexible shape support: direct attr map or nested map.
        for key in ("MarketingAttributes", "marketingAttributes", "attributes"):
            if key in data and isinstance(data[key], dict):
                return {str(k): str(v) for k, v in data[key].items()}
        return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, int, float, bool))}
    raise ValueError(f"Unsupported JSON shape in {qdf_file}")


def validate_qdf(
    qdf_name: str,
    attrs: Dict[str, str],
    expectations: Dict[str, AttributeExpectation],
    strict_undocumented: bool,
    strict_warnings: bool,
) -> QdfSummary:
    summary = QdfSummary(qdf_name=qdf_name)

    for attr_name, attr_value in attrs.items():
        summary.total_attributes += 1

        if attr_name not in expectations:
            summary.undocumented_attributes += 1
            if strict_undocumented:
                summary.invalid_attributes += 1
                summary.issues.append(f"{attr_name}='{attr_value}' undocumented")
            continue

        exp = expectations[attr_name]

        if exp.accepts_any_value:
            summary.valid_attributes += 1
            continue

        if not exp.expected_values:
            summary.skipped_attributes += 1
            continue

        # Warning-style case from original tests: numeric QDF vs enum-like CSV values.
        if is_numeric(attr_value) and all((not is_numeric(v) and not is_validation_rule(v)) for v in exp.expected_values):
            if strict_warnings:
                summary.invalid_attributes += 1
                summary.issues.append(f"{attr_name}='{attr_value}' numeric-vs-enum mismatch")
            else:
                summary.skipped_attributes += 1
            continue

        if value_matches(attr_value, exp.expected_values):
            summary.valid_attributes += 1
        else:
            summary.invalid_attributes += 1
            expected_preview = "; ".join(sorted(exp.expected_values)[:8])
            summary.issues.append(f"{attr_name}='{attr_value}' expected one of [{expected_preview}]")

    return summary


def write_summary_csv(path: Path, summaries: List[QdfSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "QDF",
            "Total",
            "Valid",
            "Invalid",
            "Skipped",
            "Undocumented",
            "Issue Count",
        ])
        for s in summaries:
            writer.writerow([
                s.qdf_name,
                s.total_attributes,
                s.valid_attributes,
                s.invalid_attributes,
                s.skipped_attributes,
                s.undocumented_attributes,
                len(s.issues),
            ])


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    lineitem_report = Path(args.lineitem_report).resolve()
    qdf_dir = Path(args.qdf_dir).resolve()

    if not qdf_dir.exists() or not qdf_dir.is_dir():
        raise SystemExit(f"QDF directory not found: {qdf_dir}")

    expectations = load_expectations(lineitem_report)
    summaries: List[QdfSummary] = []

    for qdf_file in iter_qdf_files(qdf_dir, args.qdf_glob):
        qdf_name = qdf_file.stem
        attrs = load_qdf_attributes(qdf_file)
        summaries.append(
            validate_qdf(
                qdf_name,
                attrs,
                expectations,
                strict_undocumented=args.strict_undocumented,
                strict_warnings=args.strict_warnings,
            )
        )

    total_qdfs = len(summaries)
    with_invalid = sum(1 for s in summaries if s.invalid_attributes > 0)

    payload = {
        "lineitem_report": str(lineitem_report),
        "qdf_dir": str(qdf_dir),
        "qdf_count": total_qdfs,
        "qdfs_with_invalid": with_invalid,
        "summary": [
            {
                "qdf": s.qdf_name,
                "total": s.total_attributes,
                "valid": s.valid_attributes,
                "invalid": s.invalid_attributes,
                "skipped": s.skipped_attributes,
                "undocumented": s.undocumented_attributes,
                "issues": s.issues,
            }
            for s in summaries
        ],
    }

    if args.output_json:
        write_json(Path(args.output_json), payload)
    if args.output_csv:
        write_summary_csv(Path(args.output_csv), summaries)

    print(json.dumps({"qdf_count": total_qdfs, "qdfs_with_invalid": with_invalid}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
