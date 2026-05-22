# FuseGen ReadOnly Parser

## Purpose
The FuseGen ReadOnly Parser extracts decoded fuse attributes from ReadOnly artifacts across a Flame repository and its recursive submodules.

It is intended to provide deterministic decoded value evidence, especially value_hex, for downstream workflows such as HSD mapping.

## When To Use
Use this agent when you need any of the following:
- Parse FuseGen decoded artifacts under ReadOnly folders
- Build decoded fuse attribute inventory across root and submodules
- Map features to related deduplicated fuse lists
- Produce CSV/JSON outputs with value and value_hex columns
- Provide decode-backed value_hex data for HSD rows

## Inputs
Supported source inputs:
- Local repository path
- Repository URL
- GitHub tree URL
- FFR path

Optional controls:
- branch, tag, or commit
- scope (root-only or recursive submodules)
- target feature list
- output format (csv/json)
- output path

## Outputs
Default artifact outputs under current workdir:
- ./out/fusegen/fusegen_readonly_decoded.csv
- ./out/fusegen/fusegen_readonly_decoded.json

Default feature-fuse mapping outputs under current workdir:
- ./out/fusegen/feature_fuse_mapping.csv
- ./out/fusegen/feature_fuse_mapping.json
- ./out/fusegen/feature_fuse_mapping_detailed.csv

CSV schema:
1. module
2. fuse_path
3. fuse_name
4. attribute
5. value
6. value_hex
7. decode_source

Feature-fuse mapping CSV schema:
1. module
2. feature_path
3. mapped_fuses
4. mapping_count
5. mapping_evidence
6. match_type
7. confidence

Feature-fuse detailed CSV schema:
1. module
2. feature_path
3. fuse_path
4. feature_value
5. fuse_value
6. fuse_value_hex
7. mapping_evidence
8. fuse_decode_source

## Parse Behavior
The agent scans ReadOnly folders using this priority:
1. Structured files: json, csv, tsv, xml, yaml/yml
2. Known text outputs: txt, log, map, dump
3. Fallback parser for key=value and tokenized lines

Feature-to-fuse mapping strategy:
1. Explicit same-record linkage where feature and fuse appear together
2. Shared decode block or attribute-group context
3. Module-scoped normalized token matching between feature and fuse names
4. Alias-aware linkage using SharedFusesList and crifFuseName normalization

Ambiguity behavior:
- If multiple fuses tie at the same best rank, retain all candidates
- Emit match_type and confidence to make review and downstream joins deterministic

Normalization behavior:
- value preserves decoded artifact representation
- value_hex uses decoded hex when available
- if value is decimal numeric, value_hex is derived as 0x uppercase
- if value is symbolic text, value_hex is empty

## Integration With HSD
HSD workflows can join decoded rows using:
- Primary key: fuse_path against HSD fuse accessor/path
- Secondary key: fuse_name with module context
- Feature-assisted key: feature_path context to disambiguate multiple fuse matches

Every decoded row includes decode_source for traceability.
