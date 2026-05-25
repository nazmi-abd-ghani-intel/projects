# Flame Agents README

This folder centralizes README documentation for all agent definitions in this repository.

## Agent Files
- [../flame-repo-parser.agent.md](../flame-repo-parser.agent.md)
- [../lineitem-attribute-extractor.agent.md](../lineitem-attribute-extractor.agent.md)
- [../qdf-validation-specialist.agent.md](../qdf-validation-specialist.agent.md)
- [../fusegen-readonly-parser.agent.md](../fusegen-readonly-parser.agent.md)
- [../hsd-info-extractor.agent.md](../hsd-info-extractor.agent.md)

## Flame Repo Parser
Top-level orchestration agent for Flame and HSD repository analysis.

Capabilities:
- Resolves repo path, repo URL, GitHub tree URL, or FFR path input.
- Resolves target revision and initializes recursive submodules.
- Inventories `Fuse.Set/*.cs` across root and submodules.
- Coordinates specialist agents for LineItem, QDF, HSD, and FuseGen tasks.

Delegation:
- LineItem requests: `LineItem Attribute Extractor`
- QDF validation requests: `QDF Validation Specialist`
- HSD mapping requests: `HSD Info Extractor`
- FuseGen decode requests: `FuseGen ReadOnly Parser`

## LineItem Attribute Extractor
Extracts LineItem attribute usage and expected-value logic from Flame `Fuse.Set` C# code.

Script engine:
- [../../../scripts/lineitem_attribute_parser.py](../../../scripts/lineitem_attribute_parser.py)

Highlights:
- Captures `.Value` and `.IsDefined` usage.
- Detects equality, inequality, null checks, contains checks, and numeric rules.
- Handles switch/case and default branch semantics.
- Produces deterministic report artifacts under the working directory.

## QDF Validation Specialist
Validates QDF data against LineItem expectations and reports mismatches and gaps.

Script engine:
- [../../../scripts/qdf_validation_parser.py](../../../scripts/qdf_validation_parser.py)

Highlights:
- Emits `VALID`, `INVALID`, `SKIPPED`, `UNDOCUMENTED`, and `ERROR` statuses.
- Supports operators `!x`, `>x`, `>=x`, `<x`, and `<=x`.
- Supports strict modes for undocumented values and warnings.

## HSD Info Extractor
Finds and normalizes HSD references from Flame code, then maps each HSD to associated fuse and feature context.

Highlights:
- Detects inline, variable-based, comment-based, and multi-value HSD references.
- Canonicalizes HSD IDs and emits article links.
- Returns deduplicated associated fuse and feature lists with occurrence evidence.
- Integrates with FuseGen decode output to populate `value_hex` when available.

## FuseGen ReadOnly Parser
Parses decoded fuse attributes from `ReadOnly` artifacts across root and recursive submodules.

Highlights:
- Produces value and value_hex evidence for downstream joins.
- Supports CSV and JSON outputs.
- Provides feature-to-fuse mapping outputs with confidence and evidence.

## Standard Output Expectations
- Keep generated artifacts under the current working directory.
- Prefer source-managed run folders for bundle workflows.
- Include run metadata for reproducibility when bundle orchestrators are used.

## Example Prompt Ideas
- Analyze an FFR path and report root plus submodule `Fuse.Set` inventory.
- Extract LineItem attributes in `mode=script` and generate CSV and JSON outputs.
- Validate QDF data and summarize invalid, undocumented, and skipped values.
- Extract HSD mappings and include decoded `value_hex` evidence.