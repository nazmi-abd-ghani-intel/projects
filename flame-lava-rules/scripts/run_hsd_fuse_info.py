#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

HSD_RE = re.compile(r"(?i)(?:HSD)?(\d{11})(?!\d)")
FUSE_RE = re.compile(r"(Fuses\.[A-Za-z0-9_.]+)")
FEATURE_RE = re.compile(r"(Features\.[A-Za-z0-9_.]+)")
VERILOG_RE = re.compile(r"(?i)^(\d+)'([hdb])([0-9a-f_x]+)$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Deterministic HSD fuse-info extractor with FuseGen enrichment')
    p.add_argument('--repo', required=True)
    p.add_argument('--hsd', required=True)
    p.add_argument('--decoded-csv', default='out/fusegen/fusegen_readonly_decoded.csv')
    p.add_argument('--feature-map-detailed-csv', default='out/fusegen/feature_fuse_mapping_detailed.csv')
    p.add_argument('--output-csv')
    p.add_argument('--output-json')
    p.add_argument('--window', type=int, default=160)
    p.add_argument('--bootstrap-feature-window', type=int, default=25)
    p.add_argument('--auto-bootstrap-fusegen', dest='auto_bootstrap_fusegen', action='store_true')
    p.add_argument('--no-auto-bootstrap-fusegen', dest='auto_bootstrap_fusegen', action='store_false')
    p.set_defaults(auto_bootstrap_fusegen=True)
    return p.parse_args()


def normalize_hsd(raw: str) -> str:
    m = re.search(r'(\d{11})', raw)
    if not m:
        raise SystemExit(f'Invalid HSD id: {raw}')
    return m.group(1)


def normalize_hex(value: str) -> str:
    token = value.strip().strip('"\'')
    if not token:
        return 'UNRESOLVED'

    m_verilog = VERILOG_RE.match(token.replace(' ', ''))
    if m_verilog:
        base = m_verilog.group(2).lower()
        digits = m_verilog.group(3).replace('_', '')
        try:
            if base == 'h':
                return '0x' + digits.upper()
            if base == 'd':
                return hex(int(digits, 10)).replace('X', 'x')
            if base == 'b':
                return hex(int(digits, 2)).replace('X', 'x')
        except Exception:
            return 'UNRESOLVED'

    if token.lower().startswith('0x'):
        return '0x' + token[2:].upper()
    if token.lower().startswith('0b'):
        try:
            return hex(int(token, 2)).replace('X', 'x')
        except Exception:
            return 'UNRESOLVED'
    if re.fullmatch(r'\d+', token):
        return hex(int(token)).replace('X', 'x')
    return 'UNRESOLVED'


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8', newline='') as fp:
        return list(csv.DictReader(fp))


def value_expr(line: str) -> Optional[str]:
    mapper_call = re.search(r"\bMapper\s*\.\s*GetValue\s*\(", line, flags=re.IGNORECASE)
    if mapper_call:
        tuple_pairs = re.finditer(
            r"\(\s*\"([^\"]+)\"\s*,\s*(?:\"([^\"]*)\"|([^,\)\s]+))\s*\)",
            line,
        )
        kv_parts: List[str] = []
        for pair in tuple_pairs:
            key = pair.group(1).strip()
            value = (pair.group(2) if pair.group(2) is not None else pair.group(3) or "").strip()
            kv_parts.append(f"{key}:{value}")
        if kv_parts:
            return ";".join(kv_parts)

    pats = [
        r"SetValueWithComment\(\s*([^,\)]+)",
        r"BinaryValueWithComment\(\s*([^,\)]+)",
        r"SetBinaryValueWithComment\(\s*([^,\)]+)",
        r"SetValueWithComment\s*=\s*\(\s*([^,\)]+)",
        r"BinaryValueWithComment\s*=\s*\(\s*([^,\)]+)",
        r"SetBinaryValueWithComment\s*=\s*\(\s*([^,\)]+)",
        r"FuseSetValue\s*=\s*\(\s*([^,\)]+)",
    ]
    for pat in pats:
        m = re.search(pat, line)
        if m:
            return m.group(1).strip().strip(",").strip("\"").strip(chr(39))

    m_static = re.search(r"\(\"systemstatic\"\s*,\s*\"([^\"]+)\"\)", line, flags=re.IGNORECASE)
    if m_static:
        return m_static.group(1).strip().strip("\"").strip(chr(39))

    m_assign = re.search(r"=\s*\"([^\"]+)\"", line)
    if m_assign:
        return m_assign.group(1).strip().strip("\"").strip(chr(39))

    m_quote = re.search(r"=\s*\(\s*\"([^\"]+)\"", line)
    if m_quote:
        return m_quote.group(1).strip().strip("\"").strip(chr(39))

    return None


def hsd_var_from_decl(line: str, hsd: str) -> Optional[str]:
    pat = rf'\b(?:string|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"[^"]*{re.escape(hsd)}[^"]*"'
    m = re.search(pat, line)
    return m.group(1) if m else None


def hsd_arg_token(line: str, hsd: str) -> Optional[str]:
    code = line.split('//', 1)[0]

    # Direct inline literal reference anywhere in the call/assignment.
    if hsd in code:
        return '__direct__'

    # Common pattern: Mapper.GetValue(hsd_, lookupKey, ...)
    m_first = re.search(r'(?:\w+\.)*GetValue\s*\(\s*([^,\)]+)', code)
    if m_first:
        raw_first = m_first.group(1).strip().rstrip(');').strip()
        token_first = raw_first.strip("\"'")
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token_first):
            return token_first

    m = re.search(r'\(\s*[^,]+,\s*([^\)]+)\)', code)
    if not m:
        return None

    raw = m.group(1).strip().rstrip(');').strip()
    if not raw:
        return None

    token = raw.strip("\"'")
    if hsd in token:
        return '__direct__'

    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token):
        return token

    return None


def line_in_hsd_scope(line: str, hsd: str, hsd_var: Optional[str]) -> bool:
    code = code_only(line)

    # Direct inline HSD literals always bind scope.
    if hsd in code:
        return True

    # Variable references anywhere in line should bind scope for this HSD.
    if hsd_var and re.search(rf'\b{re.escape(hsd_var)}\b', code):
        return True

    token = hsd_arg_token(line, hsd)
    if token is None:
        return False
    if token == '__direct__':
        return True
    if hsd_var:
        return token == hsd_var
    return False


def code_only(line: str) -> str:
    return line.split('//', 1)[0]


def comment_assigns_hsd_var(line: str, hsd_var: Optional[str], hsd: str) -> bool:
    if '.Comment' not in line:
        return False
    if hsd_var and re.search(rf'\.Comment\s*=\s*{re.escape(hsd_var)}\b', line):
        return True
    if hsd in line:
        return True
    return False


def brace_delta(line: str) -> int:
    code = code_only(line)
    return code.count('{') - code.count('}')


def find_block_scope_end(lines: List[str], start_index: int) -> int:
    start_depth = 0
    for k in range(0, start_index + 1):
        start_depth += brace_delta(lines[k])

    depth = start_depth
    for idx in range(start_index + 1, len(lines)):
        depth += brace_delta(lines[idx])
        if depth < start_depth:
            return idx + 1

    return len(lines)


def uniq(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def normalize_fuse_symbol(name: str) -> str:
    symbol = name.strip()
    symbol = re.sub(r'_(DF|POR|PO|HWRESET|HWReset|Reset)$', '', symbol, flags=re.IGNORECASE)
    return symbol


def fuse_leaf_from_path(fuse_path: str) -> str:
    parts = fuse_path.split('.')
    if len(parts) < 4:
        return ''
    return parts[3]


def accessor_parts(accessor: str) -> List[str]:
    token = accessor.strip().strip("\"'")
    if not token:
        return []
    parts = [p for p in token.split('.') if p]
    if not parts:
        return []

    if parts[0].lower() not in {'fuses', 'features'}:
        return parts

    call_suffixes = {
        'setvaluewithcomment',
        'binaryvaluewithcomment',
        'setbinaryvaluewithcomment',
        'fusesetvalue',
        'comment',
    }
    if parts and parts[-1].lower() in call_suffixes:
        parts = parts[:-1]
    return parts


def feature_leaf(accessor: str) -> str:
    parts = accessor_parts(accessor)
    if len(parts) >= 4 and parts[0].lower() == 'features':
        return parts[3].lower()
    return ''


def accessor_identity(accessor: str) -> str:
    parts = accessor_parts(accessor)
    if not parts:
        return accessor.lower()

    if len(parts) >= 4 and (parts[0].lower() == 'fuses' or parts[0].lower() == 'features'):
        return '.'.join(parts[:4]).lower()
    if len(parts) >= 3 and (parts[0].lower() == 'fuses' or parts[0].lower() == 'features'):
        return '.'.join(parts[:3]).lower()
    return '.'.join(parts).lower()


def parse_source_location(source: str) -> Tuple[str, int]:
    if ':' not in source:
        return source, 0
    path, line = source.rsplit(':', 1)
    try:
        return path, int(line)
    except Exception:
        return path, 0


def display_name_from_accessor(accessor: str) -> str:
    parts = accessor_parts(accessor)
    if not parts:
        return accessor.strip()
    if parts[0].lower() in {'fuses', 'features'}:
        return '.'.join(parts[1:]) if len(parts) > 1 else ''
    return '.'.join(parts)


def canonical_fuse_name(
    default_accessor: str,
    map_rows: List[Dict[str, str]],
    decoded_by_name: Dict[str, List[Dict[str, str]]],
) -> str:
    for row in map_rows:
        fuse_path = (row.get('fuse_path') or '').strip()
        if not fuse_path:
            continue
        mapped_name = display_name_from_accessor(fuse_path)
        leaf = mapped_name.split('.')[-1].lower()
        candidates = decoded_by_name.get(leaf, [])
        if not candidates and '_atom_fuse_' in leaf:
            # Normalize common alias variants to FuseGen canonical names.
            candidates = decoded_by_name.get(leaf.replace('_atom_fuse_', '_'), [])
        for cand in candidates:
            cand_path = (cand.get('fuse_path') or '').strip()
            if cand_path:
                return display_name_from_accessor(cand_path)
        return mapped_name

    default_name = display_name_from_accessor(default_accessor)
    default_leaf = default_name.split('.')[-1].lower()
    candidates = decoded_by_name.get(default_leaf, [])
    if not candidates and '_atom_fuse_' in default_leaf:
        candidates = decoded_by_name.get(default_leaf.replace('_atom_fuse_', '_'), [])
    for cand in candidates:
        cand_path = (cand.get('fuse_path') or '').strip()
        if cand_path:
            return display_name_from_accessor(cand_path)
    return default_name


def canonical_feature_name(default_accessor: str, map_rows: List[Dict[str, str]]) -> str:
    for row in map_rows:
        feature_path = (row.get('feature_path') or '').strip()
        if feature_path:
            return display_name_from_accessor(feature_path)
    return display_name_from_accessor(default_accessor)


def parse_readonly_encoding_maps(repo: Path) -> Dict[str, Dict[str, str]]:
    maps: Dict[str, Dict[str, str]] = defaultdict(dict)
    for iip in repo.rglob('*.iip'):
        p = iip.as_posix().lower()
        if '/readonly/fuses.' not in p:
            continue
        lines = iip.read_text(encoding='utf-8', errors='ignore').splitlines()
        for idx, line in enumerate(lines):
            m_fuse = re.search(r'public\s+FuseValue\s+([A-Za-z0-9_]+)\s*=>', line)
            if not m_fuse:
                continue
            fuse_key = normalize_fuse_symbol(m_fuse.group(1)).lower()
            start = max(0, idx - 260)
            block = lines[start:idx]

            enc_start = -1
            for bidx in range(len(block) - 1, -1, -1):
                if '<term>EncodingValues</term>' in block[bidx]:
                    enc_start = bidx
                    break
            if enc_start < 0:
                continue

            pending_term = ''
            for bline in block[enc_start:]:
                m_term = re.search(r'<term>([^<]+)</term>', bline)
                if m_term:
                    term = m_term.group(1).strip()
                    if term.lower() not in {'defaultvalue', 'bitoffset', 'bitwidth', 'encodingvalues'}:
                        pending_term = term
                    continue
                if not pending_term:
                    continue
                m_desc = re.search(r'<description>([^<]+)</description>', bline)
                if not m_desc:
                    continue
                cand = m_desc.group(1).strip()
                if not (VERILOG_RE.match(cand.replace(' ', '')) or cand.lower().startswith('0x') or cand.isdigit()):
                    continue
                hx = normalize_hex(cand)
                if hx != 'UNRESOLVED':
                    maps[fuse_key][pending_term.lower()] = hx
                pending_term = ''
    return maps


def resolve_symbolic_hex(fuse: str, value: str, encoding_maps: Dict[str, Dict[str, str]]) -> str:
    leaf = fuse_leaf_from_path(fuse).lower()
    token = value.strip().strip('"\\''').lower()
    if not leaf or not token:
        return 'UNRESOLVED'
    return encoding_maps.get(leaf, {}).get(token, 'UNRESOLVED')


def normalized_match_token(value: str) -> str:
    return (value or '').strip().strip('"\\''').lower()


def filter_map_rows_for_coded_value(map_rows: List[Dict[str, str]], coded_value: str) -> List[Dict[str, str]]:
    if not map_rows:
        return []

    target = normalized_match_token(coded_value)
    if not target:
        return map_rows

    # Feature-based rows should match feature_value first.
    by_feature = [r for r in map_rows if normalized_match_token(r.get('feature_value') or '') == target]
    if by_feature:
        return by_feature

    # Fuse-based rows should match fuse_value when available.
    by_fuse = [r for r in map_rows if normalized_match_token(r.get('fuse_value') or '') == target]
    if by_fuse:
        return by_fuse

    return map_rows


def best_row_value_and_hex(
    rows: List[Dict[str, str]],
    resolved_fuse: str,
    encoding_maps: Dict[str, Dict[str, str]],
) -> Optional[Tuple[str, str]]:
    if not rows:
        return None

    candidates: List[Tuple[int, str, str]] = []
    for row in rows:
        val = (row.get('fuse_value') or '').strip()
        if not val:
            continue
        hx = (row.get('fuse_value_hex') or '').strip()
        if not hx:
            hx = normalize_hex(val)
            if hx == 'UNRESOLVED':
                hx = resolve_symbolic_hex(resolved_fuse, val, encoding_maps)
        score = 0 if hx != 'UNRESOLVED' else 1
        candidates.append((score, val, hx))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1].lower(), x[2].lower()))
    _, val, hx = candidates[0]
    return val, hx


def best_value_and_hex(
    resolved_fuse: str,
    coded_value: str,
    decoded_by_path: Dict[str, List[Dict[str, str]]],
    decoded_by_name: Dict[str, List[Dict[str, str]]],
    encoding_maps: Dict[str, Dict[str, str]],
    map_rows: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, str]:
    if map_rows:
        filtered_rows = filter_map_rows_for_coded_value(map_rows, coded_value)
        chosen = best_row_value_and_hex(filtered_rows, resolved_fuse, encoding_maps)
        if chosen:
            return chosen

    drows = decoded_by_path.get(resolved_fuse.lower(), [])
    if not drows:
        drows = decoded_by_name.get(fuse_leaf_from_path(resolved_fuse).lower(), [])

    target = normalized_match_token(coded_value)
    if target and drows:
        exact = [r for r in drows if normalized_match_token(r.get('value') or '') == target]
        if exact:
            exact.sort(key=lambda r: ((r.get('value_hex') or '').strip() == 'UNRESOLVED', (r.get('value') or '').lower()))
            val = (exact[0].get('value') or '').strip()
            hx = (exact[0].get('value_hex') or '').strip() or normalize_hex(val)
            if hx == 'UNRESOLVED':
                hx = resolve_symbolic_hex(resolved_fuse, val, encoding_maps)
            return val, hx

    if drows:
        drows_sorted = sorted(
            drows,
            key=lambda r: (
                (r.get('value_hex') or '').strip() == 'UNRESOLVED',
                (r.get('value') or '').lower(),
            ),
        )
        val = (drows_sorted[0].get('value') or '').strip()
        hx = (drows_sorted[0].get('value_hex') or '').strip() or normalize_hex(val)
        if hx == 'UNRESOLVED':
            hx = resolve_symbolic_hex(resolved_fuse, val, encoding_maps)
        if val:
            return val, hx

    value = coded_value.strip()
    if not value:
        return '', 'UNRESOLVED'

    hx = normalize_hex(value)
    if hx == 'UNRESOLVED':
        hx = resolve_symbolic_hex(resolved_fuse, value, encoding_maps)
    return value, hx


def derive_feature_fuse_rows_from_cs(
    repo: Path,
    window: int,
    encoding_maps: Dict[str, Dict[str, str]],
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for cs in repo.rglob('*.cs'):
        if 'Fuse.Set' not in cs.as_posix():
            continue

        lines = cs.read_text(encoding='utf-8', errors='ignore').splitlines()
        features: List[Tuple[int, str, str]] = []
        fuses: List[Tuple[int, str, str, str]] = []

        for idx, line in enumerate(lines):
            line_features = FEATURE_RE.findall(line)
            line_fuses = FUSE_RE.findall(line)
            if line_features:
                val = value_expr(line) or ''
                for feature in line_features:
                    features.append((idx, feature, val))
            if line_fuses:
                val = value_expr(line) or ''
                for fuse in line_fuses:
                    hx = normalize_hex(val) if val else 'UNRESOLVED'
                    if hx == 'UNRESOLVED' and val:
                        hx = resolve_symbolic_hex(fuse, val, encoding_maps)
                    fuses.append((idx, fuse, val, hx))

        if not features or not fuses:
            continue

        for feature_idx, feature_path, feature_value in features:
            nearest_distance: Optional[int] = None
            for fuse_idx, _, _, _ in fuses:
                distance = abs(fuse_idx - feature_idx)
                if distance <= window and (nearest_distance is None or distance < nearest_distance):
                    nearest_distance = distance

            if nearest_distance is None:
                continue

            for fuse_idx, fuse_path, fuse_value, fuse_value_hex in fuses:
                if abs(fuse_idx - feature_idx) != nearest_distance:
                    continue
                rows.append({
                    'feature_path': feature_path,
                    'fuse_path': fuse_path,
                    'feature_value': feature_value,
                    'fuse_value': fuse_value,
                    'fuse_value_hex': fuse_value_hex,
                    'mapping_evidence': f'cs-nearest-distance:{nearest_distance}',
                    'fuse_decode_source': cs.as_posix(),
                })

    return rows


def validate_output_names(rows: List[Dict[str, str]]) -> None:
    forbidden_prefixes = ('Fuses.', 'Features.')
    forbidden_suffixes = (
        '.SetValueWithComment',
        '.BinaryValueWithComment',
        '.SetBinaryValueWithComment',
        '.FuseSetValue',
        '.Comment',
    )

    violations: List[str] = []
    for i, row in enumerate(rows, start=2):
        for col in ('fuses', 'feature'):
            val = (row.get(col) or '').strip()
            if not val:
                continue
            if val.startswith(forbidden_prefixes):
                violations.append(f'line {i} col {col}: contains accessor prefix -> {val}')
                continue
            if any(val.endswith(sfx) for sfx in forbidden_suffixes):
                violations.append(f'line {i} col {col}: contains accessor method suffix -> {val}')

    if violations:
        preview = '\n'.join(violations[:10])
        more = '' if len(violations) <= 10 else f'\n... and {len(violations)-10} more'
        raise SystemExit('Output name validation failed:\n' + preview + more)


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f'Missing repo path: {repo}')

    hsd = normalize_hsd(args.hsd)
    out_csv = Path(args.output_csv) if args.output_csv else Path(f'out/hsd/hsd_{hsd}_fuses.csv')
    out_json = Path(args.output_json) if args.output_json else Path(f'out/hsd/hsd_{hsd}_fuses.json')

    encoding_maps = parse_readonly_encoding_maps(repo)

    decoded_rows = read_csv(Path(args.decoded_csv))
    decoded_by_path: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    decoded_by_name: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in decoded_rows:
        key = (row.get('fuse_path') or '').strip().lower()
        if key:
            decoded_by_path[key].append(row)
            leaf = re.split(r'[./]', key)[-1]
            if leaf:
                decoded_by_name[leaf].append(row)
        name_key = (row.get('fuse_name') or '').strip().lower()
        if name_key:
            decoded_by_name[name_key].append(row)

    feature_rows = read_csv(Path(args.feature_map_detailed_csv))
    feature_map_bootstrap_source = 'provided_feature_map_csv'
    if not feature_rows:
        derived_rows: List[Dict[str, str]] = []
        for row in decoded_rows:
            feature_path = (row.get('feature_path') or '').strip()
            fuse_path = (row.get('fuse_path') or '').strip()
            if feature_path and fuse_path:
                derived_rows.append({
                    'feature_path': feature_path,
                    'fuse_path': fuse_path,
                    'feature_value': (row.get('feature_value') or row.get('value') or '').strip(),
                    'fuse_value': (row.get('fuse_value') or row.get('value') or '').strip(),
                    'fuse_value_hex': (row.get('fuse_value_hex') or row.get('value_hex') or '').strip(),
                })
        feature_rows = derived_rows
        if feature_rows:
            feature_map_bootstrap_source = 'decoded_csv_columns'

    if not feature_rows and args.auto_bootstrap_fusegen:
        feature_rows = derive_feature_fuse_rows_from_cs(
            repo=repo,
            window=max(1, args.bootstrap_feature_window),
            encoding_maps=encoding_maps,
        )
        if feature_rows:
            feature_map_bootstrap_source = 'fuse_set_cs_nearest'
        else:
            feature_map_bootstrap_source = 'none'

    feature_map_by_feature: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    feature_map_by_identity: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    feature_map_by_leaf: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    mapped_features_by_fuse: Dict[str, Set[str]] = defaultdict(set)
    mapped_features_by_fuse_identity: Dict[str, Set[str]] = defaultdict(set)
    map_by_feature_fuse: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    map_by_identity_feature_fuse: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in feature_rows:
        feature_path = (row.get('feature_path') or '').strip()
        fuse_path = (row.get('fuse_path') or '').strip()
        feature_key = feature_path.lower()
        fuse_key = fuse_path.lower()
        feature_id = accessor_identity(feature_path) if feature_path else ''
        fuse_id = accessor_identity(fuse_path) if fuse_path else ''
        feature_name = feature_leaf(feature_path)

        if feature_key:
            feature_map_by_feature[feature_key].append(row)
        if feature_id:
            feature_map_by_identity[feature_id].append(row)
        if feature_name:
            feature_map_by_leaf[feature_name].append(row)
        if feature_key and fuse_key:
            mapped_features_by_fuse[fuse_key].add(feature_path)
            map_by_feature_fuse[(feature_key, fuse_key)].append(row)
        if feature_id and fuse_id:
            mapped_features_by_fuse_identity[fuse_id].add(feature_path)
            map_by_identity_feature_fuse[(feature_id, fuse_id)].append(row)

    coded_entries: List[Dict[str, str]] = []
    occurrences = 0

    for cs in repo.rglob('*.cs'):
        if 'Fuse.Set' not in cs.as_posix():
            continue
        lines = cs.read_text(encoding='utf-8', errors='ignore').splitlines()
        rel = cs.relative_to(repo).as_posix()
        for i, line in enumerate(lines):
            line_code = code_only(line)
            hits = HSD_RE.findall(line_code)
            if hsd not in hits:
                continue
            occurrences += 1
            hsd_var = hsd_var_from_decl(line_code, hsd)
            end = find_block_scope_end(lines, i) if hsd_var else min(len(lines), i + args.window)
            region = lines[i:end]

            comment_scope_anchor = False
            for j, rline in enumerate(region):
                rline_code = code_only(rline)
                if not rline_code.strip():
                    continue

                if comment_assigns_hsd_var(rline_code, hsd_var, hsd):
                    comment_scope_anchor = True
                    continue

                in_direct_scope = line_in_hsd_scope(rline_code, hsd, hsd_var)
                if not in_direct_scope and comment_scope_anchor:
                    # Comment anchor ties this block to HSD; include only real programming lines.
                    if not (('Fuses.' in rline_code or 'Features.' in rline_code) and value_expr(rline_code)):
                        continue
                elif not in_direct_scope:
                    continue

                src = f'{rel}:{i+j+1}'
                coded_value = value_expr(rline_code) or ''
                line_fuses = FUSE_RE.findall(rline_code)
                line_features = FEATURE_RE.findall(rline_code)

                if line_fuses:
                    for coded in line_fuses:
                        coded_entries.append({
                            'coded_fuses': coded,
                            'coded_value': coded_value,
                            'source': src,
                        })
                elif line_features:
                    for coded in line_features:
                        coded_entries.append({
                            'coded_fuses': coded,
                            'coded_value': coded_value,
                            'source': src,
                        })

    feature_entries_by_file: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for entry in coded_entries:
        coded = entry.get('coded_fuses', '')
        if not coded.startswith('Features.'):
            continue
        src_file, src_line = parse_source_location(entry.get('source', ''))
        if src_line > 0:
            feature_entries_by_file[src_file].append((src_line, coded))

    rows: List[Dict[str, str]] = []
    unresolved = 0


    for entry in coded_entries:
        coded = entry['coded_fuses']
        coded_value = entry['coded_value']
        source = entry['source']

        if coded.startswith('Features.'):
            mapped = feature_map_by_feature.get(coded.lower(), [])
            if not mapped:
                mapped = feature_map_by_identity.get(accessor_identity(coded), [])
            if not mapped:
                mapped = feature_map_by_leaf.get(feature_leaf(coded), [])
            mapped_fuses = uniq([(r.get('fuse_path') or '').strip() for r in mapped if (r.get('fuse_path') or '').strip()])

            if not mapped_fuses:
                rows.append({
                    'coded_fuses': coded,
                    'coded_value': coded_value,
                    'fuses': '',
                    'feature': display_name_from_accessor(coded),
                    'value': coded_value,
                    'value_hex': 'UNRESOLVED',
                    'hsd': hsd,
                    'source': source,
                })
                unresolved += 1
                continue

            for resolved_fuse in mapped_fuses:
                map_rows = map_by_feature_fuse.get((coded.lower(), resolved_fuse.lower()), [])
                if not map_rows:
                    map_rows = map_by_identity_feature_fuse.get((accessor_identity(coded), accessor_identity(resolved_fuse)), [])
                resolved_value, resolved_hex = best_value_and_hex(
                    resolved_fuse=resolved_fuse,
                    coded_value=coded_value,
                    decoded_by_path=decoded_by_path,
                    decoded_by_name=decoded_by_name,
                    encoding_maps=encoding_maps,
                    map_rows=map_rows,
                )
                if resolved_hex == 'UNRESOLVED':
                    unresolved += 1

                rows.append({
                    'coded_fuses': coded,
                    'coded_value': coded_value,
                    'fuses': canonical_fuse_name(resolved_fuse, map_rows, decoded_by_name),
                    'feature': canonical_feature_name(coded, map_rows),
                    'value': resolved_value,
                    'value_hex': resolved_hex,
                    'hsd': hsd,
                    'source': source,
                })

        else:
            resolved_fuse = coded
            mapped_features = sorted(mapped_features_by_fuse.get(resolved_fuse.lower(), set()))
            if not mapped_features:
                mapped_features = sorted(mapped_features_by_fuse_identity.get(accessor_identity(resolved_fuse), set()))

            # Choose one best feature for this fuse row using nearest in-file feature occurrence.
            source_file, source_line = parse_source_location(source)
            feature_cell = ''
            best_map_rows: List[Dict[str, str]] = []
            if mapped_features:
                best_feature: Optional[str] = None
                best_distance: Optional[int] = None
                for feat_line, feat_coded in feature_entries_by_file.get(source_file, []):
                    d = abs(feat_line - source_line) if source_line > 0 else 10**9
                    map_rows = map_by_feature_fuse.get((feat_coded.lower(), resolved_fuse.lower()), [])
                    if not map_rows:
                        map_rows = map_by_identity_feature_fuse.get((accessor_identity(feat_coded), accessor_identity(resolved_fuse)), [])
                    if not map_rows:
                        continue
                    if best_distance is None or d < best_distance:
                        best_distance = d
                        best_feature = feat_coded
                        best_map_rows = map_rows

                if best_feature:
                    feature_cell = best_feature
                else:
                    feature_cell = mapped_features[0]
                    fallback_rows = map_by_feature_fuse.get((feature_cell.lower(), resolved_fuse.lower()), [])
                    if not fallback_rows:
                        fallback_rows = map_by_identity_feature_fuse.get((accessor_identity(feature_cell), accessor_identity(resolved_fuse)), [])
                    best_map_rows = fallback_rows

            resolved_value, resolved_hex = best_value_and_hex(
                resolved_fuse=resolved_fuse,
                coded_value=coded_value,
                decoded_by_path=decoded_by_path,
                decoded_by_name=decoded_by_name,
                encoding_maps=encoding_maps,
                map_rows=None,
            )
            if resolved_hex == 'UNRESOLVED':
                unresolved += 1

            rows.append({
                'coded_fuses': coded,
                'coded_value': coded_value,
                'fuses': canonical_fuse_name(resolved_fuse, best_map_rows, decoded_by_name),
                'feature': canonical_feature_name(feature_cell, best_map_rows) if feature_cell else '',
                'value': resolved_value,
                'value_hex': resolved_hex,
                'hsd': hsd,
                'source': source,
            })

    dedup: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str, str, str, str, str, str]] = set()
    for row in rows:
        key = (
            row['coded_fuses'],
            row['coded_value'],
            row['fuses'],
            row['feature'],
            row['value'],
            row['value_hex'],
            row['hsd'],
            row['source'],
        )
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)

    unresolved = sum(1 for r in dedup if r.get('value_hex') == 'UNRESOLVED')
    mapped_feature_rows = sum(1 for r in dedup if r.get('coded_fuses', '').startswith('Features.') and bool(r.get('fuses')))

    validate_output_names(dedup)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ['coded_fuses', 'coded_value', 'fuses', 'feature', 'value', 'value_hex', 'hsd', 'source']
    with out_csv.open('w', encoding='utf-8', newline='') as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(dedup)

    payload = {
        'hsd': hsd,
        'repo': str(repo),
        'rows': dedup,
        'summary': {
            'fuse_rows': len(dedup),
            'hsd_occurrences': occurrences,
            'unresolved_value_hex_rows': unresolved,
            'mapped_feature_rows': mapped_feature_rows,
            'feature_map_rows_loaded': len(feature_rows),
            'feature_map_bootstrap_source': feature_map_bootstrap_source,
            'decoded_csv_used': str(Path(args.decoded_csv)),
            'feature_map_detailed_csv_used': str(Path(args.feature_map_detailed_csv)),
        },
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    print(json.dumps({'output_csv': str(out_csv), 'output_json': str(out_json), **payload['summary']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())







