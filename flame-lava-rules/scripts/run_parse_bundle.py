#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned or "source"


def create_run_dir(output_root: Path, source_label: str, mode: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    base = slugify(source_label)
    target = output_root / base
    if mode == "reuse":
        target.mkdir(parents=True, exist_ok=True)
        return target
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = output_root / f"{base}_{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def acquire_run_lock(run_dir: Path, timeout_seconds: int) -> Path:
    lock_path = run_dir / ".run.lock"
    started = time.monotonic()

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                fp.write(json.dumps({"pid": os.getpid(), "created_utc": datetime.now(timezone.utc).isoformat()}) + "\n")
            return lock_path
        except FileExistsError:
            if timeout_seconds <= 0:
                raise SystemExit(f"Run directory is locked by another process: {lock_path}")
            if time.monotonic() - started >= timeout_seconds:
                raise SystemExit(f"Timed out waiting for run lock: {lock_path}")
            time.sleep(1)


def release_run_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


def run_cmd(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def run_capture(cmd: List[str]) -> Optional[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def is_repo_url(value: str) -> bool:
    lowered = value.lower()
    return (
        lowered.startswith("https://")
        or lowered.startswith("http://")
        or lowered.startswith("ssh://")
        or lowered.startswith("git@")
        or lowered.endswith(".git")
    )


def normalize_remote_url(url: str) -> str:
    cleaned = url.strip().lower()
    cleaned = cleaned.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned


def repo_name_from_url(url: str) -> str:
    trimmed = url.rstrip("/")
    if "/" in trimmed:
        candidate = trimmed.rsplit("/", 1)[-1]
    else:
        candidate = trimmed
    if ":" in candidate and "/" not in candidate:
        candidate = candidate.split(":", 1)[-1]
    if candidate.endswith(".git"):
        candidate = candidate[:-4]

    # Prefer compact flame repo token when available, e.g. p-nvl-s-16c.
    parts = [part for part in candidate.split(".") if part]
    if parts:
        tail = parts[-1].lower()
        if re.fullmatch(r"[pdt]-[a-z0-9-]+", tail):
            return slugify(tail)

    return slugify(candidate)


def short_ref_suffix(repo_ref: Optional[str]) -> str:
    if not repo_ref:
        return "head"
    match = re.fullmatch(r"[0-9a-fA-F]{7,40}", repo_ref.strip())
    if match:
        return repo_ref.strip()[:8].lower()
    return slugify(repo_ref)[:16] or "head"


def ensure_repo_checkout(repo_input: str, repo_ref: Optional[str], cache_root: Path) -> Path:
    direct = Path(repo_input)
    if direct.exists():
        return direct.resolve()

    if not is_repo_url(repo_input):
        return direct.resolve()

    cache_root.mkdir(parents=True, exist_ok=True)
    repo_name = repo_name_from_url(repo_input)
    suffix = short_ref_suffix(repo_ref)
    target = cache_root / f".tmp_{repo_name}_{suffix}"

    git_dir = target / ".git"
    if not git_dir.exists():
        run_cmd(["git", "clone", repo_input, str(target)])
    else:
        existing_origin = run_capture(["git", "-C", str(target), "config", "--get", "remote.origin.url"])
        if existing_origin and normalize_remote_url(existing_origin) != normalize_remote_url(repo_input):
            raise SystemExit(
                f"Repo cache folder already exists with a different origin: {target}"
            )

    if repo_ref:
        current_head = run_capture(["git", "-C", str(target), "rev-parse", "HEAD"])
        if not current_head or (current_head != repo_ref and not current_head.startswith(repo_ref)):
            run_cmd(["git", "-C", str(target), "fetch", "--all", "--tags"])
            run_cmd(["git", "-C", str(target), "checkout", repo_ref])

    run_cmd(["git", "-C", str(target), "submodule", "update", "--init", "--recursive"])
    return target.resolve()


def find_fusedef_path(source: str) -> Optional[Path]:
    source_path = Path(source)
    if source_path.is_file() and source_path.name.lower() == "fusedef.txt":
        return source_path
    if not source_path.exists() or not source_path.is_dir():
        return None
    fusedef = source_path / "fusedef.txt"
    if fusedef.exists() and fusedef.is_file():
        return fusedef
    return None


def parse_repo_url_and_ref_from_fusedef(fusedef_path: Path) -> Optional[Tuple[str, str]]:
    pattern = re.compile(r"https?://[^\s|]+/commit/([0-9a-fA-F]{7,40})")
    for raw in fusedef_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:120]:
        line = raw.strip()
        if not line.startswith("#"):
            continue
        match = pattern.search(line)
        if not match:
            continue
        commit = match.group(1)
        commit_url = match.group(0)
        repo_url = commit_url[: commit_url.rfind("/commit/")]
        return repo_url, commit
    return None


def resolve_repo_input_and_ref(args: argparse.Namespace) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if args.repo:
        return args.repo, args.repo_ref, None

    fusedef_path = find_fusedef_path(args.source)
    if fusedef_path is None:
        return args.source, args.repo_ref, None

    parsed = parse_repo_url_and_ref_from_fusedef(fusedef_path)
    if parsed is None:
        return args.source, args.repo_ref, str(fusedef_path)

    repo_url, commit = parsed
    return repo_url, (args.repo_ref or commit), str(fusedef_path)


def run_capture_lines(cmd: List[str]) -> List[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def resolved_path_if_exists(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    path = Path(raw)
    return str(path.resolve()) if path.exists() else None


def normalize_default_branch(symbolic_ref: Optional[str]) -> Optional[str]:
    if not symbolic_ref:
        return None
    marker = "refs/remotes/origin/"
    if symbolic_ref.startswith(marker):
        return symbolic_ref[len(marker):]
    return symbolic_ref


def parse_submodule_status_line(raw_line: str) -> Optional[Tuple[str, str]]:
    raw = raw_line.strip()
    if not raw:
        return None
    marker = raw[0]
    body = raw[1:].strip() if marker in " +-U" else raw
    parts = body.split()
    if len(parts) < 2:
        return None
    pinned_commit, rel_path = parts[0], parts[1]
    return pinned_commit, rel_path

def extract_qdf_names_from_lineitemdata(lineitemdata_path: Path) -> List[str]:
    pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
    names: set[str] = set()

    for raw in lineitemdata_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split(":", 1)[0].strip()
        if pattern.fullmatch(token):
            names.add(token)

    return sorted(names)


def is_submodule_qdf_path(path: Path) -> bool:
    return ".sm" in path.parts


def find_main_repo_qdf_dir(source_dir: Path) -> Optional[Path]:
    if not source_dir.exists() or not source_dir.is_dir():
        return None

    # Prefer the top-level Product repo QDF folder, not die-level submodule QDF folders.
    for child in sorted(source_dir.iterdir()):
        if not child.is_dir():
            continue
        if not child.name.endswith("_Product"):
            continue
        candidate = child / "QDFs"
        if candidate.exists() and candidate.is_dir():
            return candidate

    fallback = source_dir / "QDFs"
    if fallback.exists() and fallback.is_dir():
        return fallback
    return None


def resolve_qdf_dir(
    source: str,
    requested_qdf_dir: Optional[str],
    compat_mode: Optional[str],
    repo_dir: Optional[Path],
) -> str:
    source_dir = Path(source)
    main_repo_qdf_dir = find_main_repo_qdf_dir(source_dir)

    if requested_qdf_dir:
        requested = Path(requested_qdf_dir)
        if requested.exists() and is_submodule_qdf_path(requested) and main_repo_qdf_dir is not None:
            return main_repo_qdf_dir.as_posix()
        return requested_qdf_dir

    if main_repo_qdf_dir is not None:
        return main_repo_qdf_dir.as_posix()

    if repo_dir is not None:
        repo_qdf_dir = find_main_repo_qdf_dir(repo_dir)
        if repo_qdf_dir is not None:
            return repo_qdf_dir.as_posix()

    if compat_mode == "ffr":
        return "out/ffr/qdf-json"

    raise SystemExit("--qdf-dir is required for qdf mode (or use --compat-mode ffr)")



def find_lineitemdata_path(source_dir: Path) -> Optional[Path]:
    if not source_dir.exists() or not source_dir.is_dir():
        return None

    direct = source_dir / "lineitemdata.txt"
    if direct.exists() and direct.is_file():
        return direct

    # Prefer Product publish artifact over any submodule layout.
    for child in sorted(source_dir.iterdir()):
        if not child.is_dir() or not child.name.endswith("_Product"):
            continue
        publish = child / "PublishFiles" / "lineitemdata.txt"
        if publish.exists() and publish.is_file():
            return publish

    return None


def collect_repo_entries(initial_repo_paths: List[str]) -> List[Dict[str, Optional[str]]]:
    entries: List[Dict[str, Optional[str]]] = []
    seen: set[str] = set()

    def scan(repo_path: Path, is_submodule: bool, parent_repo: Optional[Path], pinned_commit: Optional[str]) -> None:
        resolved = repo_path.resolve()
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)

        entries.append(
            {
                "path": key,
                "is_submodule": is_submodule,
                "parent_repo": str(parent_repo.resolve()) if parent_repo else None,
                "pinned_commit": pinned_commit,
            }
        )

        for line in run_capture_lines(["git", "-C", key, "submodule", "status"]):
            parsed = parse_submodule_status_line(line)
            if not parsed:
                continue
            child_pinned_commit, rel_path = parsed
            child_path = (resolved / rel_path).resolve()
            if child_path.exists():
                scan(child_path, True, resolved, child_pinned_commit)

    for raw_path in initial_repo_paths:
        path_obj = Path(raw_path)
        resolved = path_obj.resolve() if path_obj.exists() else path_obj
        if resolved.exists():
            scan(resolved, False, None, None)

    return entries


def build_repo_sources(repo_paths: List[str]) -> List[Dict[str, object]]:
    entries = collect_repo_entries(repo_paths)
    sources: List[Dict[str, object]] = []

    for entry in entries:
        path = str(entry["path"])
        origin_url = run_capture(["git", "-C", path, "config", "--get", "remote.origin.url"])
        head = run_capture(["git", "-C", path, "rev-parse", "HEAD"])
        branch = run_capture(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"])
        default_branch = normalize_default_branch(
            run_capture(["git", "-C", path, "symbolic-ref", "refs/remotes/origin/HEAD"])
        )

        sources.append(
            {
                "path": path,
                "origin_url": origin_url,
                "head": head,
                "branch": branch,
                "default_branch": default_branch,
                "is_submodule": bool(entry["is_submodule"]),
                "parent_repo": entry["parent_repo"],
                "pinned_commit": entry["pinned_commit"],
            }
        )

    return sources


def write_run_metadata(
    run_dir: Path,
    args: argparse.Namespace,
    generated: Dict[str, str],
    repo_resolved: Optional[Path],
    qdf_dir_used: Optional[str],
    lineitem_report_used: Optional[str],
) -> Path:
    source_resolved = args.resolved_source
    if not source_resolved:
        source_path = Path(args.source)
        source_resolved = str(source_path.resolve()) if source_path.exists() else None

    repo_resolved_str = args.resolved_repo
    if not repo_resolved_str and repo_resolved is not None:
        repo_resolved_str = str(repo_resolved)

    flame_repos = [resolved_path_if_exists(path) or path for path in (args.flame_repo_path or [])]
    if not flame_repos and repo_resolved_str:
        flame_repos = [repo_resolved_str]

    repo_sources = build_repo_sources(flame_repos)
    flame_repos_parsed = [str(item["path"]) for item in repo_sources]

    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "workflow_type": args.type,
        "compat_mode": args.compat_mode,
        "ffr_source": {
            "input": args.source,
            "resolved": source_resolved,
        },
        "flame_git_repos_parsed": flame_repos_parsed,
        "flame_git_repo_sources": repo_sources,
        "inputs": {
            "repo_input": args.repo,
            "repo_resolved": repo_resolved_str,
            "hsd": args.hsd,
            "decoded_csv": args.decoded_csv,
            "decoded_csv_resolved": resolved_path_if_exists(args.decoded_csv),
            "feature_map_detailed_csv": args.feature_map_detailed_csv,
            "feature_map_detailed_csv_resolved": resolved_path_if_exists(args.feature_map_detailed_csv),
            "lineitem_report": lineitem_report_used,
            "lineitem_report_resolved": resolved_path_if_exists(lineitem_report_used),
            "qdf_dir": qdf_dir_used,
            "qdf_dir_resolved": resolved_path_if_exists(qdf_dir_used),
            "lira": args.lira,
            "lira_resolved": resolved_path_if_exists(args.lira),
        },
        "files": generated,
    }
    metadata_path = run_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lineitem/qdf/hsd parsers with managed output folders")
    parser.add_argument("--source", required=True, help="Source identifier (FFR path or repo path/URL)")
    parser.add_argument("--type", choices=["lineitem", "qdf", "both", "hsd"], default="both")
    parser.add_argument("--repo", help="Repo path for lineitem parser (defaults to --source)")
    parser.add_argument("--repo-ref", help="Optional repo revision (commit/tag/branch) used when --repo is a URL")
    parser.add_argument(
        "--repo-cache-root",
        default="out/repos",
        help="Repo cache root used when --repo is a URL (creates .tmp_<repo>_<shortref> folders)",
    )
    parser.add_argument("--lineitem-report", help="LineItem CSV for qdf mode (required for qdf-only unless compat ffr default exists)")
    parser.add_argument("--qdf-dir", help="QDF JSON directory for qdf mode")
    parser.add_argument("--hsd", help="HSD ID for hsd mode (for example 16026402689)")
    parser.add_argument("--decoded-csv", default="out/fusegen/fusegen_readonly_decoded.csv", help="Decoded fuse CSV for hsd mode")
    parser.add_argument("--feature-map-detailed-csv", default="out/fusegen/feature_fuse_mapping_detailed.csv", help="Feature-fuse detailed mapping CSV for hsd mode")
    parser.add_argument("--lira", help="Optional LineItem.lira path for YES/NO LIRA validation in lineitem output")
    parser.add_argument("--compat-mode", choices=["ffr"], help="Optional compat mode for defaults")
    parser.add_argument("--output-root", default="out/runs", help="Root folder where managed run dirs are created (hsd defaults to out/hsd when not overridden)")
    parser.add_argument(
        "--run-dir-mode",
        choices=["reuse", "unique"],
        default="reuse",
        help="reuse: single folder per source label, unique: timestamped folder when label already exists",
    )
    parser.add_argument(
        "--run-lock-timeout",
        type=int,
        default=0,
        help="Seconds to wait for run-folder lock (0 = fail fast if another run is active)",
    )
    parser.add_argument("--label", help="Optional custom folder label")
    parser.add_argument("--resolved-source", help="Resolved absolute source path supplied by orchestrator/agent")
    parser.add_argument("--resolved-repo", help="Resolved absolute repo path supplied by orchestrator/agent")
    parser.add_argument(
        "--flame-repo-path",
        action="append",
        default=[],
        help="Repeatable repo path list (root first, then submodules) supplied by orchestrator/agent",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_label = args.label or Path(args.source).name or args.source
    output_root = args.output_root
    if args.type == "hsd" and output_root == "out/runs":
        output_root = "out/hsd"
    if args.type == "hsd" and args.hsd and not args.label:
        source_label = f"hsd_{args.hsd}"
    run_dir = create_run_dir(Path(output_root).resolve(), source_label, args.run_dir_mode)
    run_lock_path = acquire_run_lock(run_dir, args.run_lock_timeout)

    try:
        python_exe = sys.executable
        generated: Dict[str, str] = {}

        lineitem_csv = run_dir / "LineItemAttributes_Report.csv"
        lineitem_json = run_dir / "lineitem_attributes.json"

        repo_resolved: Optional[Path] = None
        qdf_dir_used: Optional[str] = None
        lineitem_report_used: Optional[str] = None
        fusedef_used: Optional[str] = None

        repo_input, repo_ref, fusedef_used = resolve_repo_input_and_ref(args)

        should_prepare_repo = args.type in {"lineitem", "both", "hsd"} or bool(args.repo)
        if should_prepare_repo and repo_input:
            repo_resolved = ensure_repo_checkout(
                repo_input=repo_input,
                repo_ref=repo_ref,
                cache_root=Path(args.repo_cache_root).resolve(),
            )

        if args.type == "hsd":
            if repo_resolved is None:
                raise SystemExit("Unable to resolve repository for hsd parsing")
            if not args.hsd:
                raise SystemExit("--hsd is required for hsd mode")

            hsd_csv = run_dir / f"hsd_{args.hsd}_fuses.csv"
            hsd_json = run_dir / f"hsd_{args.hsd}_fuses.json"

            cmd = [
                python_exe,
                "scripts/run_hsd_fuse_info.py",
                "--repo",
                str(repo_resolved),
                "--hsd",
                str(args.hsd),
                "--decoded-csv",
                str(args.decoded_csv),
                "--feature-map-detailed-csv",
                str(args.feature_map_detailed_csv),
                "--output-csv",
                str(hsd_csv),
                "--output-json",
                str(hsd_json),
            ]
            run_cmd(cmd)
            generated["hsd_csv"] = str(hsd_csv)
            generated["hsd_json"] = str(hsd_json)

        if args.type in {"lineitem", "both"}:
            if repo_resolved is None:
                raise SystemExit("Unable to resolve repository for lineitem parsing")
            cmd = [
                python_exe,
                "scripts/lineitem_attribute_parser.py",
                "--repo",
                str(repo_resolved),
                "--output-csv",
                str(lineitem_csv),
                "--output-json",
                str(lineitem_json),
            ]
            if args.qdf_dir:
                cmd.extend([
                    "--qdf-dir",
                    str(args.qdf_dir),
                ])
            if args.lira:
                cmd.extend([
                    "--lira",
                    str(args.lira),
                ])
            run_cmd(cmd)
            generated["lineitem_csv"] = str(lineitem_csv)
            generated["lineitem_json"] = str(lineitem_json)

        if args.type in {"qdf", "both"}:
            lineitem_report = args.lineitem_report
            if not lineitem_report and args.type == "both":
                lineitem_report = str(lineitem_csv)
            if not lineitem_report and args.compat_mode == "ffr":
                lineitem_report = "out/ffr/lineitem_attributes_from_ffr.csv"
            if not lineitem_report:
                raise SystemExit("--lineitem-report is required for qdf mode (or use --type both)")

            qdf_dir = resolve_qdf_dir(args.source, args.qdf_dir, args.compat_mode, repo_resolved)

            qdf_allowlist_path: Optional[Path] = None
            source_candidate = Path(args.source)
            lineitemdata_path = find_lineitemdata_path(source_candidate)
            if lineitemdata_path and lineitemdata_path.exists():
                qdf_names = extract_qdf_names_from_lineitemdata(lineitemdata_path)
                if qdf_names:
                    qdf_allowlist_path = run_dir / "qdf_allowlist_from_lineitemdata.txt"
                    qdf_allowlist_path.write_text("\n".join(qdf_names) + "\n", encoding="utf-8")
                    generated["qdf_allowlist_file"] = str(qdf_allowlist_path)

            lineitem_report_used = str(lineitem_report)
            qdf_dir_used = str(qdf_dir)

            qdf_csv = run_dir / "qdf_validation_from_ffr.csv"
            qdf_json = run_dir / "qdf_validation_from_ffr.json"
            heatmap_csv = run_dir / "qdf_validation_heatmap.csv"
            heatmap_json = run_dir / "qdf_validation_heatmap.json"
            heatmap_xlsx = run_dir / "QDF_LIRA_Validation_Heatmap.xlsx"

            cmd = [
                python_exe,
                "scripts/qdf_validation_parser.py",
                "--lineitem-report",
                str(lineitem_report),
                "--qdf-dir",
                str(qdf_dir),
                "--output-csv",
                str(qdf_csv),
                "--output-json",
                str(qdf_json),
                "--output-heatmap-csv",
                str(heatmap_csv),
                "--output-heatmap-json",
                str(heatmap_json),
                "--output-heatmap-xlsx",
                str(heatmap_xlsx),
            ]
            if qdf_allowlist_path is not None:
                cmd.extend(["--qdf-allowlist-file", str(qdf_allowlist_path)])
            run_cmd(cmd)
            generated.update(
                {
                    "qdf_csv": str(qdf_csv),
                    "qdf_json": str(qdf_json),
                    "heatmap_csv": str(heatmap_csv),
                    "heatmap_json": str(heatmap_json),
                    "heatmap_xlsx": str(heatmap_xlsx),
                }
            )

        if fusedef_used:
            generated["fusedef_used"] = fusedef_used

        metadata_path = write_run_metadata(
            run_dir=run_dir,
            args=args,
            generated=generated,
            repo_resolved=repo_resolved,
            qdf_dir_used=qdf_dir_used,
            lineitem_report_used=lineitem_report_used,
        )
        generated["run_metadata_json"] = str(metadata_path)

        print(json.dumps({"run_dir": str(run_dir), "files": generated}, indent=2))
        return 0
    finally:
        release_run_lock(run_lock_path)


if __name__ == "__main__":
    raise SystemExit(main())


