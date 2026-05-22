#!/usr/bin/env python3
"""
LineItem attribute parser for Flame-style Fuse.Set C# code.

Hybrid usage:
- Script mode: deterministic extraction for CI/repeatable reporting
- Agent mode: orchestration, repo resolution, and narrative summaries
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


ATTR_REF_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.(Value|IsDefined)\b")
EQ_LITERAL_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*==\s*\"([^\"]+)\"")
NEQ_LITERAL_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*!=\s*\"([^\"]+)\"")
EQ_IDENT_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*(==|!=)\s*([A-Za-z_][A-Za-z0-9_\.]*)")
NULL_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*(==|!=)\s*null\b")
CONTAINS_RE = re.compile(r"\blineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\.Contains\s*\(\s*([^\)]+?)\s*\)")
NUMERIC_RE = re.compile(
    r"Convert\.ToDouble\s*\(\s*lineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*\)\s*([><]=?|==|!=)\s*(-?\d+(?:\.\d+)?)"
)
NUMERIC_CONSUME_RE = re.compile(r"Convert\.ToDouble\s*\(\s*lineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*\)")
SWITCH_RE = re.compile(r"\bswitch\s*\(\s*lineItem\.([A-Z_][A-Za-z0-9_]*)\.Value\s*\)")
CASE_LITERAL_RE = re.compile(r"\bcase\s+\"([^\"]+)\"\s*:")
CASE_BOOL_RE = re.compile(r"\bcase\s+(true|false)\s*:")
DEFAULT_RE = re.compile(r"\bdefault\s*:")
BREAK_RE = re.compile(r"\bbreak\s*;")
DEFAULT_ERROR_RE = re.compile(r"\bthrow\b|\bRuleErrorHandler\.Throw\w*\b")


@dataclass
class AttributeInfo:
    name: str
    expected_values: Set[str] = field(default_factory=set)
    condition_patterns: Set[str] = field(default_factory=set)
    used_in_modules: Set[str] = field(default_factory=set)
    used_in_files: Set[str] = field(default_factory=set)
    collection_names: Set[str] = field(default_factory=set)
    display_names: Set[str] = field(default_factory=set)
    notes: Set[str] = field(default_factory=set)
    valid_in_lira: str = "UNKNOWN"
    total_usages: int = 0


@dataclass
class ScanStats:
    files_scanned: int = 0
    value_refs: int = 0
    isdefined_refs: int = 0
    null_checks: int = 0
    switch_on_value: int = 0
    contains_checks: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract LineItem attribute usage from Fuse.Set C# files")
    parser.add_argument("--repo", required=True, help="Local repository root path")
    parser.add_argument("--output-json", help="Output JSON path")
    parser.add_argument("--output-csv", help="Output CSV path")
    parser.add_argument("--lira", help="Path to LineItem.lira for validation")
    parser.add_argument("--qdf-dir", help="Optional QDF JSON directory used to enrich collection/display metadata")
    parser.add_argument("--include-non-fuseset", action="store_true", help="Scan all .cs files, not only Fuse.Set")
    return parser.parse_args()


def iter_cs_files(repo: Path, include_non_fuseset: bool) -> Iterable[Path]:
    for path in repo.rglob("*.cs"):
        low = str(path).lower()
        if "\\obj\\" in low or "\\bin\\" in low or "/obj/" in low or "/bin/" in low:
            continue
        if not include_non_fuseset and "fuse.set" not in low:
            continue
        yield path


def load_lira_attributes(lira_path: Optional[Path]) -> Set[str]:
    if not lira_path or not lira_path.exists():
        return set()
    prop_re = re.compile(r"public\s+LineItemString\s+([A-Za-z_][A-Za-z0-9_]*)\s*=>\s*_")
    out: Set[str] = set()
    for line in lira_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = prop_re.search(line)
        if m:
            out.add(m.group(1))
    return out


def strip_inline_comment(line: str) -> str:
    idx = line.find("//")
    if idx < 0:
        return line
    quote_count = line[:idx].count('"') - line[:idx].count('\\"')
    if quote_count % 2 == 0:
        return line[:idx]
    return line


def module_name(repo: Path, path: Path) -> str:
    rel = path.relative_to(repo)
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == ".sm":
        return parts[1]
    return "root"



def iter_qdf_files(qdf_dir: Path) -> Iterable[Path]:
    for path in sorted(qdf_dir.glob("*.json")):
        if path.is_file():
            yield path


def enrich_from_qdf(attributes: Dict[str, AttributeInfo], qdf_dir: Optional[Path]) -> None:
    if qdf_dir is None or not qdf_dir.exists():
        return

    for qdf_file in iter_qdf_files(qdf_dir):
        try:
            data = json.loads(qdf_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        collections = data.get("collections") if isinstance(data, dict) else None
        if not isinstance(collections, list):
            continue

        for collection in collections:
            if not isinstance(collection, dict):
                continue
            collection_name = str(collection.get("collectionName") or "").strip()
            items = collection.get("attributes")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                attr_name = str(item.get("attributeName") or "").strip()
                if not attr_name or attr_name not in attributes:
                    continue
                display_name = str(item.get("displayName") or "").strip()
                info = attributes[attr_name]
                if collection_name:
                    info.collection_names.add(collection_name)
                if display_name:
                    info.display_names.add(display_name)
def parse_repo(repo: Path, include_non_fuseset: bool, valid_lira: Set[str]) -> Tuple[Dict[str, AttributeInfo], ScanStats]:
    attributes: Dict[str, AttributeInfo] = {}
    stats = ScanStats()

    for file_path in iter_cs_files(repo, include_non_fuseset):
        stats.files_scanned += 1
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_block_comment = False

        current_switch_attr: Optional[str] = None
        switch_depth = 0
        pending_default_attr: Optional[str] = None

        def record_default_behavior(attr: str, token: str, pattern: str) -> None:
            info = attributes.setdefault(attr, AttributeInfo(name=attr))
            info.expected_values.add(token)
            info.condition_patterns.add(pattern)

        for line_no, line in enumerate(lines, start=1):
            raw = line
            trimmed = raw.strip()

            if in_block_comment:
                if "*/" in raw:
                    in_block_comment = False
                continue
            if "/*" in raw:
                if "*/" not in raw:
                    in_block_comment = True
                continue

            if trimmed.startswith("//"):
                continue

            code = strip_inline_comment(raw)
            code_trim = code.strip()
            if not code_trim:
                continue

            is_exception_line = (
                "throw new Exception" in code
                or "throw new ArgumentException" in code
                or "throw new InvalidOperationException" in code
                or "RuleErrorHandler.Throw" in code
            )

            sw = SWITCH_RE.search(code)
            if sw:
                current_switch_attr = sw.group(1)
                switch_depth = code.count("{") - code.count("}")
                stats.switch_on_value += 1
            elif current_switch_attr is not None:
                switch_depth += code.count("{") - code.count("}")
                if switch_depth < 0:
                    if pending_default_attr:
                        record_default_behavior(pending_default_attr, "<any-other-value>", "SWITCH_DEFAULT")
                        pending_default_attr = None
                    current_switch_attr = None
                    switch_depth = 0

            if pending_default_attr:
                if DEFAULT_ERROR_RE.search(code):
                    record_default_behavior(pending_default_attr, "<any-other-value:ERROR>", "SWITCH_DEFAULT_ERROR")
                    pending_default_attr = None
                elif BREAK_RE.search(code):
                    record_default_behavior(pending_default_attr, "<any-other-value:default>", "SWITCH_DEFAULT")
                    pending_default_attr = None
                elif CASE_LITERAL_RE.search(code) or CASE_BOOL_RE.search(code) or DEFAULT_RE.search(code):
                    record_default_behavior(pending_default_attr, "<any-other-value>", "SWITCH_DEFAULT")
                    pending_default_attr = None

            for m in ATTR_REF_RE.finditer(code):
                attr = m.group(1)
                ref_kind = m.group(2)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.used_in_files.add(str(file_path.relative_to(repo)))
                info.used_in_modules.add(module_name(repo, file_path))
                info.total_usages += 1
                if ref_kind == "Value":
                    stats.value_refs += 1
                    if NUMERIC_CONSUME_RE.search(code) or "Converter." in code:
                        info.condition_patterns.add("NUMERIC_DERIVED")
                        info.notes.add("NUMERIC_DERIVED: value used in numeric conversion/derivation")
                else:
                    stats.isdefined_refs += 1
                    info.condition_patterns.add("IS_DEFINED")

            if is_exception_line:
                continue

            for m in EQ_LITERAL_RE.finditer(code):
                attr, val = m.group(1), m.group(2)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.expected_values.add(val)
                info.condition_patterns.add("EQUALS_LITERAL")

            for m in NEQ_LITERAL_RE.finditer(code):
                attr, val = m.group(1), m.group(2)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.expected_values.add(val)
                info.expected_values.add(f"!{val}")
                info.condition_patterns.add("NOT_EQUALS_LITERAL")

            for m in EQ_IDENT_RE.finditer(code):
                attr, op, ident = m.group(1), m.group(2), m.group(3)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.notes.add(f"IDENT_COMPARISON: {op} {ident}")
                info.condition_patterns.add("IDENTIFIER_COMPARISON")

            for m in NULL_RE.finditer(code):
                attr, op = m.group(1), m.group(2)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.condition_patterns.add("NULL_CHECK")
                info.notes.add(f"NULL_CHECK: {op} null")
                stats.null_checks += 1

            for m in CONTAINS_RE.finditer(code):
                attr, needle = m.group(1), m.group(2).strip()
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                info.condition_patterns.add("CONTAINS")
                info.notes.add(f"CONTAINS: {needle}")
                stats.contains_checks += 1

            for m in NUMERIC_RE.finditer(code):
                attr, op, val = m.group(1), m.group(2), m.group(3)
                info = attributes.setdefault(attr, AttributeInfo(name=attr))
                marker = f"{op}{val}"
                info.expected_values.add(marker)
                info.condition_patterns.add("NUMERIC_COMPARE")

            if current_switch_attr:
                info = attributes.setdefault(current_switch_attr, AttributeInfo(name=current_switch_attr))
                for cm in CASE_LITERAL_RE.finditer(code):
                    info.expected_values.add(cm.group(1))
                    info.condition_patterns.add("SWITCH_CASE_LITERAL")
                for bm in CASE_BOOL_RE.finditer(code):
                    info.expected_values.add(bm.group(1).lower())
                    info.condition_patterns.add("SWITCH_CASE_BOOL")
                if DEFAULT_RE.search(code):
                    if DEFAULT_ERROR_RE.search(code):
                        record_default_behavior(current_switch_attr, "<any-other-value:ERROR>", "SWITCH_DEFAULT_ERROR")
                    elif BREAK_RE.search(code):
                        record_default_behavior(current_switch_attr, "<any-other-value:default>", "SWITCH_DEFAULT")
                    else:
                        pending_default_attr = current_switch_attr

        if pending_default_attr:
            record_default_behavior(pending_default_attr, "<any-other-value>", "SWITCH_DEFAULT")

    for attr, info in attributes.items():
        if valid_lira:
            info.valid_in_lira = "YES" if attr in valid_lira else "NO"

    return attributes, stats

def to_rows(attributes: Dict[str, AttributeInfo]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for attr in sorted(attributes):
        info = attributes[attr]
        expected_values_sorted = sorted(info.expected_values)
        notes_parts: List[str] = []
        if info.condition_patterns:
            notes_parts.append("Patterns: " + "; ".join(sorted(info.condition_patterns)))
        if info.notes:
            notes_parts.extend(sorted(info.notes))

        rows.append(
            {
                "Attribute Name": info.name,
                "Display Name": "; ".join(sorted(info.display_names)),
                "Collection Name": "; ".join(sorted(info.collection_names)),
                "Valid in LIRA": info.valid_in_lira,
                "Expected Values": "; ".join(expected_values_sorted),
                "Value Count": str(len(expected_values_sorted)),
                "Used In Dies": "; ".join(sorted(info.used_in_modules)),
                "Die Count": str(len(info.used_in_modules)),
                "Used In Files": "; ".join(sorted(info.used_in_files)),
                "File Count": str(len(info.used_in_files)),
                "Total Usages": str(info.total_usages),
                "Notes": "; ".join(notes_parts),
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        raise SystemExit(f"Repository path not found: {repo}")

    lira_path = Path(args.lira).resolve() if args.lira else None
    valid_lira = load_lira_attributes(lira_path)

    attrs, stats = parse_repo(repo, args.include_non_fuseset, valid_lira)
    qdf_dir = Path(args.qdf_dir).resolve() if args.qdf_dir else None
    enrich_from_qdf(attrs, qdf_dir)
    rows = to_rows(attrs)

    payload = {
        "repo": str(repo),
        "files_scanned": stats.files_scanned,
        "pattern_counts": {
            "value_refs": stats.value_refs,
            "isdefined_refs": stats.isdefined_refs,
            "null_checks": stats.null_checks,
            "switch_on_value": stats.switch_on_value,
            "contains_checks": stats.contains_checks,
        },
        "attributes": rows,
    }

    if args.output_json:
        write_json(Path(args.output_json), payload)
    if args.output_csv:
        write_csv(Path(args.output_csv), rows)

    print(json.dumps({"attributes": len(rows), "files_scanned": stats.files_scanned}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


