#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

def slugify(value: str) -> str:
 cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', value.strip())
 cleaned = re.sub(r'_+', '_', cleaned).strip('._-')
 return cleaned or 'source'

def create_run_dir(output_root: Path, source_label: str) -> Path:
 output_root.mkdir(parents=True, exist_ok=True)
 base = slugify(source_label)
 target = output_root / base
 if target.exists():
  stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
  target = output_root / f'{base}_{stamp}'
 target.mkdir(parents=True, exist_ok=False)
 return target

def run_cmd(cmd: List[str]) -> None:
 proc = subprocess.run(cmd, text=True)
 if proc.returncode != 0:
  raise SystemExit(proc.returncode)

def resolved_path_if_exists(raw: Optional[str]) -> Optional[str]:
 if not raw:
  return None
 path = Path(raw)
 return str(path.resolve()) if path.exists() else None

def write_run_metadata(
 run_dir: Path,
 args: argparse.Namespace,
 generated: Dict[str, str],
 repo_resolved: Optional[Path],
 qdf_dir_used: Optional[str],
 lineitem_report_used: Optional[str],
) -> Path:
 source_path = Path(args.source)
 source_resolved = str(source_path.resolve()) if source_path.exists() else None
 flame_repos: List[str] = []
 if repo_resolved is not None:
  flame_repos.append(str(repo_resolved))
 payload = {
  'created_utc': datetime.now(timezone.utc).isoformat(),
  'run_dir': str(run_dir),
  'workflow_type': args.type,
  'compat_mode': args.compat_mode,
  'ffr_source': {
   'input': args.source,
   'resolved': source_resolved,
  },
  'flame_git_repos_parsed': flame_repos,
  'inputs': {
   'repo_input': args.repo,
   'repo_resolved': str(repo_resolved) if repo_resolved else None,
   'lineitem_report': lineitem_report_used,
   'lineitem_report_resolved': resolved_path_if_exists(lineitem_report_used),
   'qdf_dir': qdf_dir_used,
   'qdf_dir_resolved': resolved_path_if_exists(qdf_dir_used),
  },
  'files': generated,
 }
 metadata_path = run_dir / 'run_metadata.json'
 metadata_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
 return metadata_path

def parse_args() -> argparse.Namespace:
 parser = argparse.ArgumentParser(description='Run lineitem/qdf parsers with managed output folders')
 parser.add_argument('--source', required=True, help='Source identifier (FFR path or repo path/URL)')
 parser.add_argument('--type', choices=['lineitem', 'qdf', 'both'], default='both')
 parser.add_argument('--repo', help='Repo path for lineitem parser (defaults to --source)')
 parser.add_argument('--lineitem-report', help='LineItem CSV for qdf mode (required for qdf-only unless compat ffr default exists)')
 parser.add_argument('--qdf-dir', help='QDF JSON directory for qdf mode')
 parser.add_argument('--compat-mode', choices=['ffr'], help='Optional compat mode for defaults')
 parser.add_argument('--output-root', default='out/runs', help='Root folder where managed run dirs are created')
 parser.add_argument('--label', help='Optional custom folder label')
 return parser.parse_args()

def main() -> int:
 args = parse_args()
 source_label = args.label or Path(args.source).name or args.source
 run_dir = create_run_dir(Path(args.output_root).resolve(), source_label)
 python_exe = sys.executable
 generated: Dict[str, str] = {}
 lineitem_csv = run_dir / 'LineItemAttributes_Report.csv'
 lineitem_json = run_dir / 'lineitem_attributes.json'
 repo_resolved: Optional[Path] = None
 qdf_dir_used: Optional[str] = None
 lineitem_report_used: Optional[str] = None
 if args.type in {'lineitem', 'both'}:
  repo_resolved = Path(args.repo or args.source).resolve()
  cmd = [
   python_exe,
   'scripts/lineitem_attribute_parser.py',
   '--repo',
   str(repo_resolved),
   '--output-csv',
   str(lineitem_csv),
   '--output-json',
   str(lineitem_json),
  ]
  run_cmd(cmd)
  generated['lineitem_csv'] = str(lineitem_csv)
  generated['lineitem_json'] = str(lineitem_json)
 if args.type in {'qdf', 'both'}:
  lineitem_report = args.lineitem_report
  if not lineitem_report and args.type == 'both':
   lineitem_report = str(lineitem_csv)
  if not lineitem_report and args.compat_mode == 'ffr':
   lineitem_report = 'out/ffr/lineitem_attributes_from_ffr.csv'
  if not lineitem_report:
   raise SystemExit('--lineitem-report is required for qdf mode (or use --type both)')
  qdf_dir = args.qdf_dir or ('out/ffr/qdf-json' if args.compat_mode == 'ffr' else None)
  if not qdf_dir:
   raise SystemExit('--qdf-dir is required for qdf mode (or use --compat-mode ffr)')
  lineitem_report_used = str(lineitem_report)
  qdf_dir_used = str(qdf_dir)
  qdf_csv = run_dir / 'qdf_validation_from_ffr.csv'
  qdf_json = run_dir / 'qdf_validation_from_ffr.json'
  heatmap_csv = run_dir / 'qdf_validation_heatmap.csv'
  heatmap_json = run_dir / 'qdf_validation_heatmap.json'
  heatmap_xlsx = run_dir / 'QDF_LIRA_Validation_Heatmap.xlsx'
  cmd = [
   python_exe,
   'scripts/qdf_validation_parser.py',
   '--lineitem-report',
   str(lineitem_report),
   '--qdf-dir',
   str(qdf_dir),
   '--output-csv',
   str(qdf_csv),
   '--output-json',
   str(qdf_json),
   '--output-heatmap-csv',
   str(heatmap_csv),
   '--output-heatmap-json',
   str(heatmap_json),
   '--output-heatmap-xlsx',
   str(heatmap_xlsx),
  ]
  run_cmd(cmd)
  generated.update({
   'qdf_csv': str(qdf_csv),
   'qdf_json': str(qdf_json),
   'heatmap_csv': str(heatmap_csv),
   'heatmap_json': str(heatmap_json),
   'heatmap_xlsx': str(heatmap_xlsx),
  })
 metadata_path = write_run_metadata(
  run_dir=run_dir,
  args=args,
  generated=generated,
  repo_resolved=repo_resolved,
  qdf_dir_used=qdf_dir_used,
  lineitem_report_used=lineitem_report_used,
 )
 generated['run_metadata_json'] = str(metadata_path)
 print(json.dumps({'run_dir': str(run_dir), 'files': generated}, indent=2))
 return 0

if __name__ == '__main__':
 raise SystemExit(main())

