#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

FUSE_PAIR_RE = re.compile(r'\{\s*(Fuses\.[A-Za-z0-9_.]+)\s*,\s*"([^"]+)"\s*\},?')
CLASS_RE = re.compile(r'public\s+class\s+([A-Za-z0-9_]+)\s*:\s*IFlameFeatureIP')
FEATURE_ADD_RE = re.compile(r'_allFeatures\.Add\("([^"]+)"')
FEATURE_INDEX_RE = re.compile(r'_allFeatures\["([^"]+)"\]')
VALUE_ADD_RE = re.compile(r'\.Add\(\s*"([^"]+)"\s*,')
VALUE_LITERAL_RE = re.compile(r'^\s*"([^"]+)"\s*,\s*$')


def norm(s: str) -> str:
    return (s or '').strip().lower()


def norm_hex(value: str) -> str:
    t = (value or '').strip()
    if not t:
        return 'UNRESOLVED'
    if t.lower().startswith('0x'):
        return '0x' + t[2:].upper()
    if re.fullmatch(r'\d+', t):
        return hex(int(t)).replace('X', 'x')
    m = re.fullmatch(r"(?i)(\d+)'([hdb])([0-9a-f_x]+)", t.replace(' ', ''))
    if m:
        base = m.group(2).lower()
        digits = m.group(3).replace('_', '')
        if base == 'h':
            return '0x' + digits.upper()
        if base == 'd':
            return hex(int(digits, 10)).replace('X', 'x')
        if base == 'b':
            return hex(int(digits, 2)).replace('X', 'x')
    return 'UNRESOLVED'


def load_decoded(path: Path) -> Tuple[
    Dict[Tuple[str, str], str],
    Dict[Tuple[str, str], str],
    Dict[Tuple[str, str], str],
    Dict[Tuple[str, str], str],
]:
    by_pair: Dict[Tuple[str, str], str] = {}
    by_source: Dict[Tuple[str, str], str] = {}
    by_leaf_pair: Dict[Tuple[str, str], str] = {}
    by_leaf_source: Dict[Tuple[str, str], str] = {}

    with path.open('r', encoding='utf-8', newline='') as fp:
        for row in csv.DictReader(fp):
            fuse_path = (row.get('fuse_path') or '').strip()
            value = (row.get('value') or '').strip()
            value_hex = (row.get('value_hex') or '').strip() or 'UNRESOLVED'
            source = (row.get('source') or '').strip()
            if not fuse_path or not value:
                continue

            key = (norm(fuse_path), norm(value))
            cur = by_pair.get(key)
            if cur is None or (cur == 'UNRESOLVED' and value_hex != 'UNRESOLVED'):
                by_pair[key] = value_hex
                if source:
                    by_source[key] = source

            leaf = fuse_path.split('.')[-1]
            if leaf:
                lkey = (norm(leaf), norm(value))
                lcur = by_leaf_pair.get(lkey)
                if lcur is None or (lcur == 'UNRESOLVED' and value_hex != 'UNRESOLVED'):
                    by_leaf_pair[lkey] = value_hex
                    if source:
                        by_leaf_source[lkey] = source

    return by_pair, by_source, by_leaf_pair, by_leaf_source


def parse_features(
    repo: Path,
    decoded_hex: Dict[Tuple[str, str], str],
    decoded_src: Dict[Tuple[str, str], str],
    decoded_leaf_hex: Dict[Tuple[str, str], str],
    decoded_leaf_src: Dict[Tuple[str, str], str],
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for p in repo.rglob('*.features'):
        lower = p.as_posix().lower()
        if '/readonly/features/' not in lower:
            continue

        text = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        cls = ''
        current_feature = ''
        current_value = ''
        saw_featurevalues = False
        expecting_value_literal = False

        for i, line in enumerate(text, start=1):
            if not cls:
                mcls = CLASS_RE.search(line)
                if mcls:
                    cls = mcls.group(1)

            madd = FEATURE_ADD_RE.search(line)
            if madd:
                current_feature = madd.group(1)
                current_value = ''
                saw_featurevalues = False
                expecting_value_literal = False

            mindex = FEATURE_INDEX_RE.search(line)
            if mindex:
                current_feature = mindex.group(1)

            if '.FeatureValues' in line:
                saw_featurevalues = True

            if saw_featurevalues and '.Add(' in line:
                mval_inline = VALUE_ADD_RE.search(line)
                if mval_inline:
                    current_value = mval_inline.group(1)
                    expecting_value_literal = False
                else:
                    expecting_value_literal = True
            elif expecting_value_literal:
                mval_literal = VALUE_LITERAL_RE.search(line)
                if mval_literal:
                    current_value = mval_literal.group(1)
                    expecting_value_literal = False

            for mfuse in FUSE_PAIR_RE.finditer(line):
                fuse_path = mfuse.group(1)
                fuse_value = mfuse.group(2)
                feature_path = f'Features.{cls}.{current_feature}' if cls and current_feature else ''

                key = (norm(fuse_path), norm(fuse_value))
                leaf_key = (norm(fuse_path.split('.')[-1]), norm(fuse_value))

                value_hex = decoded_hex.get(key)
                decode_source = decoded_src.get(key, '')
                if value_hex is None:
                    value_hex = decoded_leaf_hex.get(leaf_key)
                    decode_source = decoded_leaf_src.get(leaf_key, decode_source)
                if value_hex is None:
                    value_hex = norm_hex(fuse_value)
                if not decode_source:
                    decode_source = f'{p.as_posix()}:{i}'

                rows.append({
                    'feature_path': feature_path,
                    'fuse_path': fuse_path,
                    'feature_value': current_value,
                    'fuse_value': fuse_value,
                    'fuse_value_hex': value_hex,
                    'mapping_evidence': 'readonly_feature_fuse_pairs',
                    'fuse_decode_source': decode_source,
                })
    return rows


def dedup(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen = set()
    for r in rows:
        k = (
            r['feature_path'].lower(),
            r['fuse_path'].lower(),
            r['feature_value'].lower(),
            r['fuse_value'].lower(),
        )
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='Build ReadOnly-derived feature->fuse mapping csv')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--decoded-csv', required=True)
    ap.add_argument('--output-csv', required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    decoded = Path(args.decoded_csv)
    out_csv = Path(args.output_csv)

    decoded_hex, decoded_src, decoded_leaf_hex, decoded_leaf_src = load_decoded(decoded)
    rows = dedup(parse_features(repo, decoded_hex, decoded_src, decoded_leaf_hex, decoded_leaf_src))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        'feature_path',
        'fuse_path',
        'feature_value',
        'fuse_value',
        'fuse_value_hex',
        'mapping_evidence',
        'fuse_decode_source',
    ]
    with out_csv.open('w', encoding='utf-8', newline='') as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f'rows={len(rows)} output={out_csv.as_posix()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
