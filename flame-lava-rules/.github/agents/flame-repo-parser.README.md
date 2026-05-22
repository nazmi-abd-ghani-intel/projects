# Flame Repo Parser README

## Agent File
- [.github/agents/flame-repo-parser.agent.md](.github/agents/flame-repo-parser.agent.md)

## Purpose
Flame Repo Parser is the top-level orchestration agent for Flame/HSD repository analysis. It resolves input sources (repo URL/path or FFR path), maps submodules, inventories Fuse.Set code, and coordinates specialist agents for deeper tasks.

## Supported Inputs
- Repository path
- Repository URL
- GitHub tree URL (`.../tree/<branch-or-tag>`)
- FFR/fuse folder path containing `fusedef.txt`
- Optional branch/tag/commit
- Optional extraction mode (`auto|script|agent`)

## Core Workflow
1. Resolve input source and revision.
2. For FFR paths, resolve `fusedef.txt` and derive repo if needed.
3. Discover and initialize recursive submodules.
4. Inventory `Fuse.Set/*.cs` across root and submodules.
5. Produce architecture/convention/risk summary.
6. Delegate specialized tasks when requested.

## Automatic Delegation
- Delegates LineItem-focused requests to:
  - [.github/agents/lineitem-attribute-extractor.agent.md](.github/agents/lineitem-attribute-extractor.agent.md)
- Delegates QDF-focused requests to:
  - [.github/agents/qdf-validation-specialist.agent.md](.github/agents/qdf-validation-specialist.agent.md)

## Mode Behavior
- `auto` (default): best-maintenance mode; script-first in specialists with agent fallback.
- `script`: deterministic output emphasis.
- `agent`: exploratory analysis when script execution is unavailable or intentionally bypassed.

## Output Sections
Expected report order:
1. Input Resolution
2. Repository Snapshot
3. Submodule Topology
4. Fuse.Set Inventory
5. LineItem Attribute Extraction (when relevant)
6. Key Conventions
7. Build and Validation Flow
8. Architecture Map
9. Risks and Unknowns
10. Suggested Next Steps

## Example Prompts
- Analyze this FFR path with submodules and show Fuse.Set inventory.
- Parse this GitHub tree URL and summarize repository conventions.
- Run in `mode=script` and include QDF validation highlights.
