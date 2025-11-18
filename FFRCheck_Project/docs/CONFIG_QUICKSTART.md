# Quick Reference: Config-Based Defaults

## ⚡ Quick Setup

**1. Edit `config.json`:**
```json
{
  "default_arguments": {
    "input_dir": "YOUR/INPUT/PATH",
    "output_dir": "output",
    "sspec": "L15H",
    "ube": "./input_files/your.ube",
    "ituff": "./input_files/itf/",
    "log": true,
    "html_stats": true
  }
}
```

**2. Run with minimal command:**
```bash
py -3.14 -m src.main
```

That's it! All defaults loaded from config. 🎉

---

## 🎯 Common Scenarios

### Scenario 1: Same Project, Different Runs
**Config**: Set input_dir and output_dir
**Command**: `py -3.14 -m src.main`
**Result**: Process with configured defaults

---

### Scenario 2: Override One Setting
**Config**: `"sspec": "L15H"`
**Command**: `py -3.14 -m src.main -sspec "*"`
**Result**: Uses "*" instead of "L15H"

---

### Scenario 3: Multiple Projects
**Setup**: Keep multiple config files
```bash
config_nvl.json
config_arl.json
```
**Usage**: Copy the one you need
```bash
copy config_nvl.json config.json
py -3.14 -m src.main
```

---

## 📝 What You Can Configure

| Setting | Example | Notes |
|---------|---------|-------|
| `input_dir` | `"I:/fuse/..."` | Can use relative or absolute |
| `output_dir` | `"results"` | Default: "output" |
| `sspec` | `"L15H"` or `"*"` | QDF specification |
| `ube` | `"./file.ube"` | UBE file path |
| `mtlolf` | `"./MTL.xml"` | MTL_OLF file path |
| `ituff` | `"./itf/"` | ITF directory |
| `log` | `true` / `false` | Enable logging |
| `html_stats` | `true` / `false` | Generate HTML |

---

## 💡 Pro Tips

1. **Use `null` for required args**:
   ```json
   "input_dir": null  // Must provide via command line
   ```

2. **Relative paths work**:
   ```json
   "ube": "./input_files/latest.ube"
   ```

3. **Check what's configured**:
   ```bash
   py -3.14 -m src.main --help
   ```

4. **Command line always wins**:
   Config says `"log": false`, but `-log` flag enables it

---

## 🚀 Real Example

**Before** (typing this every time):
```bash
py -3.14 -m src.main "I:/fuse/release/NVL/NVL_HX_Int/NVL_HX_Int_A1_25WW44P0" output -sspec L15H -ube .\input_files\P5461880SM_6197.ube -ituff .\input_files\P5461880SM_6197\ -log --html-stats
```

**After** (config.json):
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

**New command**:
```bash
py -3.14 -m src.main
```

**Saved**: 150+ characters per run! ⌨️💨

---

## ✅ Summary

| Feature | Benefit |
|---------|---------|
| 📋 Config defaults | Type less, run faster |
| 🔄 Easy override | Command line wins |
| 🎯 Project-specific | Different configs per project |
| 👥 Team sharing | Share configs with team |
| 📝 Self-documenting | Config shows standard usage |

**Full docs**: `docs/CONFIG_ARGUMENTS.md`
