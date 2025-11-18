# ITF SSID Mapping Configuration Guide

## Overview

The SSID mapping table has been moved from hardcoded Python code to `config.json` for easy customization without code changes. This allows you to:

- **Switch between different test programs** (prog_RAP, lockout_RAP, etc.)
- **Add new mappings** for different products
- **Maintain multiple configurations** for different environments
- **No code changes required** - just edit JSON file

---

## Configuration Location

**File**: `config.json`

**Section**: `itf_parser`

```json
{
  "itf_parser": {
    "active_mapping": "lockout_RAP",
    "ssid_mappings": {
      "prog_RAP": [...],
      "lockout_RAP": [...]
    }
  }
}
```

---

## Switching Between Mappings

### Current Active Mapping: `lockout_RAP`

To switch to a different mapping, change the `active_mapping` value:

```json
"active_mapping": "prog_RAP"
```

**Available Profiles**:
- `prog_RAP` - HVM RAP test program
- `lockout_RAP` - Lockout RAP test program

---

## Adding a New Mapping Profile

### Example: Adding "custom_test" Profile

1. **Add new mapping array** in `config.json`:

```json
{
  "itf_parser": {
    "active_mapping": "custom_test",
    "ssid_mappings": {
      "prog_RAP": [...],
      "lockout_RAP": [...],
      "custom_test": [
        {
          "domain": "IPC::FUS",
          "register": "CPU0",
          "ssid": "U1.U5",
          "tname_patterns": ["YOUR_CUSTOM_TNAME_PATTERN_CPU0"]
        },
        {
          "domain": "IPG::FUS",
          "register": "GCD",
          "ssid": "U1.U4",
          "tname_patterns": ["YOUR_CUSTOM_TNAME_PATTERN_GCD"]
        }
      ]
    }
  }
}
```

2. **Set as active**:
```json
"active_mapping": "custom_test"
```

3. **Run your tool** - it will automatically use the new mapping!

---

## Mapping Structure

Each mapping entry has 4 fields:

```json
{
  "domain": "IPC::FUS",          // Domain identifier
  "register": "CPU0",            // Register name
  "ssid": "U1.U5",              // SSID (Socket Site ID)
  "tname_patterns": [            // List of TNAME patterns to match
    "FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU0"
  ]
}
```

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `domain` | String | Fuse domain identifier | `"IPC::FUS"`, `"IPG::FUS"`, `"IPH::FUS"`, `"IPP::FUS"` |
| `register` | String | Register name | `"CPU0"`, `"CPU1"`, `"GCD"`, `"HUB"`, `"PCD"`, `"OSSE"` |
| `ssid` | String | Socket Site ID | `"U1.U5"`, `"U1.U4"`, `"U1.U2"`, `"U1.U3"` |
| `tname_patterns` | Array | TNAME patterns to match (supports regex) | `["FACTFUSBURNCPUNOM_.*_CPU0"]` |

---

## Pattern Matching

TNAME patterns support:
- **Exact string matching**: `"FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU0"`
- **Regex patterns**: `"FACTFUSBURNCPUNOM_.*_LOCKBIT_RAP_CPU0"`

### Examples

```json
{
  "tname_patterns": [
    "EXACT_MATCH_STRING",
    "PATTERN_WITH_.*_WILDCARD",
    "ANOTHER_PATTERN_[0-9]+"
  ]
}
```

---

## Current Mappings Reference

### lockout_RAP (Default)

| Domain | Register | SSID | TNAME Pattern |
|--------|----------|------|---------------|
| IPC::FUS | CPU0 | U1.U5 | FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU0 |
| IPC::FUS | CPU1 | U1.U6 | FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU1 |
| IPG::FUS | GCD | U1.U4 | FACTFUSBURNGCDNOM_X_X_X_X_LOCKBIT_RAP_GCD |
| IPH::FUS | HUB | U1.U2 | FACTFUSBURNHUBNOM_X_X_X_X_LOCKBIT_RAP_HUB |
| IPP::FUS | PCD | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_LOCKBITRAP_PCD |
| IPP::FUS | OSSE | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_OSSE_LOCKBITRAP_OSSE |
| IPP::FUS | OSSE_INTELIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_OSSEINTELIFP_LOCKBITRAP_OSSE_INTELIFP |
| IPP::FUS | PCD_OEMIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_PCDOEMIFP_LOCKBITRAP_PCD_OEMIFP |
| IPP::FUS | PCD_INTELIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_PCDINTELIFP_LOCKBITRAP_PCD_INTELIFP |

### prog_RAP

| Domain | Register | SSID | TNAME Pattern |
|--------|----------|------|---------------|
| IPC::FUS | CPU0 | U1.U5 | FACTFUSBURNCPUNOM_X_X_X_X_HVM_RAP_CPU0 |
| IPC::FUS | CPU1 | U1.U6 | FACTFUSBURNCPUNOM_X_X_X_X_HVM_RAP_CPU1 |
| IPG::FUS | GCD | U1.U4 | FACTFUSBURNGCDNOM_X_X_X_X_HVM_RAP_GCD |
| IPH::FUS | HUB | U1.U2 | FACTFUSBURNHUBNOM_X_X_X_X_HVM_RAP_HUB |
| IPP::FUS | PCD | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_HVMRAP_PCD |
| IPP::FUS | OSSE | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_OSSE_HVMRAP_OSSE |
| IPP::FUS | OSSE_INTELIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_OSSEINTELIFP_HVMRAP_OSSE_INTELIFP |
| IPP::FUS | PCD_OEMIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_PCDOEMIFP_HVMRAP_PCD_OEMIFP |
| IPP::FUS | PCD_INTELIFP | U1.U3 | FACTFUSBURNPCDNOM_X_X_X_X_PCDINTELIFP_HVMRAP_PCD_INTELIFP |

---

## Usage Examples

### Example 1: Switch to prog_RAP

Edit `config.json`:
```json
"active_mapping": "prog_RAP"
```

Run your command:
```bash
py -3.14 -m src.main "I:/fuse/..." output -sspec L15H -ituff .\input\
```

Output:
```
📋 Loaded 9 SSID mappings for profile: prog_RAP
```

### Example 2: Create Product-Specific Mapping

For a new product "NVL_Product_X", add:

```json
{
  "itf_parser": {
    "active_mapping": "nvl_product_x",
    "ssid_mappings": {
      "nvl_product_x": [
        {
          "domain": "IPC::FUS",
          "register": "CPU0",
          "ssid": "U1.U5",
          "tname_patterns": ["NVL_PRODUCTX_CPU0_PATTERN"]
        }
      ]
    }
  }
}
```

### Example 3: Multi-Pattern Matching

Match multiple TNAME variations:

```json
{
  "domain": "IPC::FUS",
  "register": "CPU0",
  "ssid": "U1.U5",
  "tname_patterns": [
    "FACTFUSBURNCPUNOM_V1_.*_CPU0",
    "FACTFUSBURNCPUNOM_V2_.*_CPU0",
    "ALTERNATIVE_TNAME_CPU0"
  ]
}
```

---

## Benefits of Config-Based Mapping

✅ **No Code Changes** - Edit JSON, not Python  
✅ **Quick Switching** - Change one line to switch profiles  
✅ **Multiple Products** - Maintain separate configs  
✅ **Version Control** - Track config changes separately  
✅ **Easy Maintenance** - Non-programmers can update  
✅ **Testing** - Easy to create test-specific mappings  

---

## Troubleshooting

### No Mappings Loaded

**Error**: `⚠️  Warning: No SSID mapping found for 'your_profile'`

**Solution**: 
1. Check `active_mapping` value matches a key in `ssid_mappings`
2. Verify JSON syntax is correct (use JSON validator)

### TNAME Not Matching

**Problem**: ITF file processed but no TNAMEs found

**Solution**:
1. Check your TNAME patterns match actual TNAMEs in ITF file
2. Add regex patterns if TNAMEs vary
3. Enable debug logging to see TNAME matching details

### JSON Syntax Error

**Problem**: Config file not loading

**Solution**:
1. Validate JSON at https://jsonlint.com
2. Check for missing commas or brackets
3. Ensure all strings are in double quotes

---

## Migration from Old Code

**Before** (Hardcoded in Python):
```python
SSID_MAPPING_TABLE = [
    ('IPC::FUS', 'CPU0', 'U1.U5', ['PATTERN']),
]
```

**After** (In config.json):
```json
{
  "domain": "IPC::FUS",
  "register": "CPU0",
  "ssid": "U1.U5",
  "tname_patterns": ["PATTERN"]
}
```

**No code changes needed** - ITFParser automatically loads from config!

---

## Command Line Override (Future Enhancement)

You could extend this to allow command-line profile selection:

```bash
py -3.14 -m src.main ... --itf-profile prog_RAP
```

This would override the `active_mapping` in config.json.
