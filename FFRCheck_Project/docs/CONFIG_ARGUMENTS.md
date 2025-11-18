# Command-Line Arguments in config.json

## 🎯 Overview

You can now configure **default command-line arguments** in `config.json` to avoid typing the same parameters repeatedly!

---

## 📝 Configuration Section

In `config.json`, find the `default_arguments` section:

```json
{
  "default_arguments": {
    "description": "Default values for command-line arguments. Can be overridden via CLI.",
    "input_dir": null,
    "output_dir": "output",
    "sspec": null,
    "ube": null,
    "mtlolf": null,
    "ituff": null,
    "log": false,
    "html_stats": true,
    "comment": "Set values here to avoid typing them every time. null = required on command line"
  }
}
```

---

## 🔧 Configurable Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `input_dir` | String/null | `null` | Input directory (required if not set) |
| `output_dir` | String | `"output"` | Output directory |
| `sspec` | String/null | `null` | QDF specification (e.g., "L15H" or "*") |
| `ube` | String/null | `null` | UBE file path |
| `mtlolf` | String/null | `null` | MTL_OLF.xml file path |
| `ituff` | String/null | `null` | ITF directory path |
| `log` | Boolean | `false` | Enable console logging |
| `html_stats` | Boolean | `true` | Generate HTML report |

---

## 💡 Usage Examples

### Example 1: Set Common Paths

**Scenario**: You always process files from the same location

**config.json**:
```json
{
  "default_arguments": {
    "input_dir": "I:/fuse/release/NVL/NVL_HX_Int/NVL_HX_Int_A1_25WW44P0",
    "output_dir": "output",
    "sspec": "L15H",
    "ube": "./input_files/P5461880SM_6197.ube",
    "ituff": "./input_files/P5461880SM_6197/",
    "log": true,
    "html_stats": true
  }
}
```

**Before** (Long command):
```bash
py -3.14 -m src.main "I:/fuse/release/NVL/NVL_HX_Int/NVL_HX_Int_A1_25WW44P0" output -sspec L15H -ube .\input_files\P5461880SM_6197.ube -ituff .\input_files\P5461880SM_6197\ -log --html-stats
```

**After** (Short command):
```bash
py -3.14 -m src.main
```

✨ All arguments loaded from config!

---

### Example 2: Set Partial Defaults

**Scenario**: Always use same output dir and options, but vary input

**config.json**:
```json
{
  "default_arguments": {
    "input_dir": null,
    "output_dir": "my_results",
    "sspec": "*",
    "log": true,
    "html_stats": true
  }
}
```

**Command** (only specify input):
```bash
py -3.14 -m src.main "I:/fuse/release/NVL/..."
```

**Result**:
- ✅ `input_dir` from command line
- ✅ `output_dir` = "my_results"
- ✅ `sspec` = "*" (all QDFs)
- ✅ `log` = true
- ✅ `html_stats` = true

---

### Example 3: Override Config Values

**Scenario**: Config has defaults, but you want to override for one run

**config.json**:
```json
{
  "default_arguments": {
    "sspec": "L15H",
    "log": false
  }
}
```

**Command** (override sspec and log):
```bash
py -3.14 -m src.main input_dir output -sspec "L0V8,L0VS" -log
```

**Result**:
- ✅ Uses `L0V8,L0VS` (overrides config's "L15H")
- ✅ Enables logging (overrides config's false)

**🔑 Command-line arguments ALWAYS override config values!**

---

## 🚀 Common Configurations

### Configuration 1: Daily Testing Setup
```json
{
  "default_arguments": {
    "output_dir": "daily_test_results",
    "sspec": "*",
    "log": true,
    "html_stats": true
  }
}
```
**Usage**: `py -3.14 -m src.main <input_dir>`

---

### Configuration 2: Quick Analysis (No Logs)
```json
{
  "default_arguments": {
    "output_dir": "quick_output",
    "log": false,
    "html_stats": false
  }
}
```
**Usage**: `py -3.14 -m src.main <input_dir> -sspec L15H`

---

### Configuration 3: Full Processing Pipeline
```json
{
  "default_arguments": {
    "input_dir": "I:/fuse/release/NVL/NVL_HX_Int/NVL_HX_Int_A1_25WW44P0",
    "output_dir": "full_results",
    "sspec": "*",
    "ube": "./input_files/latest.ube",
    "ituff": "./input_files/itf/",
    "log": true,
    "html_stats": true
  }
}
```
**Usage**: `py -3.14 -m src.main` (no arguments needed!)

---

## 📋 Help Command

View current defaults:
```bash
py -3.14 -m src.main --help
```

Output shows configured defaults:
```
usage: python -m src.main [-h] [-sspec SSPEC (default: L15H)] ...

arguments:
  input_dir             Input directory (required if not in config)
  output_dir            Output directory (default: output)
  -sspec SSPEC          QDF specification (default: L15H)
  -ube UBE              UBE file path (default: ./input.ube)
  ...

Note: Default values can be configured in config.json under "default_arguments" section
```

---

## ⚠️ Important Notes

### 1. `null` vs Value
- `null` = **no default**, must provide via command line (or it uses fallback)
- `"value"` = **has default**, optional on command line

### 2. Required Arguments
- `input_dir` must be provided either:
  - In config.json: `"input_dir": "path/to/input"`
  - On command line: `py -3.14 -m src.main "path/to/input"`

### 3. Boolean Arguments
- Set in config: `"log": true`
- Override with flag: `-log` or `--log`

### 4. Path Format
Use forward slashes or escaped backslashes:
- ✅ `"I:/fuse/release/..."`
- ✅ `"I:\\fuse\\release\\..."`
- ✅ `"./relative/path"`
- ❌ `"I:\fuse\release\"` (unescaped backslashes)

---

## 🎨 Best Practices

### 1. **Project-Specific Configs**
Keep different `config.json` files for different projects:
```bash
project_A/
  ├── config.json  (paths for Project A)
  └── ...
project_B/
  ├── config.json  (paths for Project B)
  └── ...
```

### 2. **Environment Variables**
For sensitive paths, consider using environment variables:
```json
{
  "default_arguments": {
    "input_dir": "${FUSE_DATA_DIR}",
    "output_dir": "${RESULTS_DIR}"
  }
}
```
*(Note: This requires additional implementation)*

### 3. **Version Control**
Create two config files:
- `config.json` - Local settings (gitignored)
- `config.example.json` - Template (committed)

```bash
# .gitignore
config.json

# Git tracks only the example
git add config.example.json
```

### 4. **Documentation**
Add comments via the `comment` field:
```json
{
  "default_arguments": {
    "input_dir": "I:/fuse/...",
    "comment": "Updated 2025-11-18 for NVL HX Int testing"
  }
}
```

---

## 🔍 Troubleshooting

### Issue: "input_dir is required"
**Cause**: `input_dir` is `null` in config and not provided on command line

**Fix**: Either set in config:
```json
"input_dir": "path/to/input"
```
Or provide on command line:
```bash
py -3.14 -m src.main "path/to/input"
```

---

### Issue: Path not found
**Cause**: Relative paths in config may not work from different directories

**Fix**: Use absolute paths:
```json
"input_dir": "C:/full/path/to/input"
```
Or run from project root directory.

---

### Issue: Config not loading
**Cause**: JSON syntax error

**Fix**: Validate at https://jsonlint.com
- Check for missing commas
- Ensure double quotes (not single)
- No trailing commas

---

## 📊 Priority Order

When the same argument is specified multiple places:

1. **Command Line** (highest priority)
2. **config.json defaults**
3. **Code defaults** (lowest priority)

Example:
```json
// config.json
"log": false
```
```bash
# Command line
py -3.14 -m src.main input output -log
```
**Result**: Logging is **enabled** (command line wins)

---

## ✨ Benefits

| Benefit | Description |
|---------|-------------|
| 🚀 **Faster Testing** | No need to type long commands |
| 📋 **Reproducible** | Same config = same results |
| 🔧 **Flexible** | Easy to override when needed |
| 👥 **Team Sharing** | Share config files with team |
| 📝 **Documentation** | Config shows standard usage |
| ⚡ **Quick Switching** | Multiple configs for scenarios |

---

## 🎓 Complete Example

**Scenario**: Daily testing of multiple products

**Setup**:
```bash
project/
  ├── config_product_a.json
  ├── config_product_b.json
  └── src/
```

**config_product_a.json**:
```json
{
  "default_arguments": {
    "input_dir": "I:/fuse/ProductA",
    "output_dir": "results_A",
    "sspec": "L15H",
    "ube": "./input/productA.ube",
    "log": true
  }
}
```

**config_product_b.json**:
```json
{
  "default_arguments": {
    "input_dir": "I:/fuse/ProductB",
    "output_dir": "results_B",
    "sspec": "L0V8",
    "ube": "./input/productB.ube",
    "log": true
  }
}
```

**Usage**:
```bash
# Test Product A
copy config_product_a.json config.json
py -3.14 -m src.main

# Test Product B
copy config_product_b.json config.json
py -3.14 -m src.main
```

---

## 🎉 Summary

- ✅ Set defaults in `config.json` under `default_arguments`
- ✅ Run with fewer/no command-line arguments
- ✅ Override config values via command line anytime
- ✅ Saves time and reduces errors
- ✅ Makes automation easier

**Your config file is now your project's command-line memory!** 🧠
