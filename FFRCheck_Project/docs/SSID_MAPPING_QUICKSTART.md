# SSID Mapping Migration - Quick Reference

## ✅ What Changed

**Before**: SSID mappings hardcoded in `src/parsers/itf_parser.py`
```python
SSID_MAPPING_TABLE = [
    ('IPC::FUS', 'CPU0', 'U1.U5', ['PATTERN']),
]
```

**After**: SSID mappings in `config.json`
```json
{
  "itf_parser": {
    "active_mapping": "lockout_RAP",
    "ssid_mappings": {
      "lockout_RAP": [...]
    }
  }
}
```

---

## 🎯 Benefits

| Before | After |
|--------|-------|
| Edit Python code | Edit JSON file |
| Restart required | Config reload only |
| One mapping at a time | Multiple profiles available |
| Developer needed | Anyone can edit |
| Hard to switch profiles | Change one line |

---

## 🚀 How to Use

### Switch Profiles

Edit `config.json`, change this line:
```json
"active_mapping": "prog_RAP"  // Was: "lockout_RAP"
```

### Available Profiles
- `lockout_RAP` (default) - Lockout test program
- `prog_RAP` - Programming test program

### Verify Profile Loaded
When you run the tool, you'll see:
```
📋 Loaded 9 SSID mappings for profile: lockout_RAP
```

---

## 📝 Adding New Profiles

1. Open `config.json`
2. Add new profile under `ssid_mappings`:

```json
{
  "itf_parser": {
    "active_mapping": "my_custom_profile",
    "ssid_mappings": {
      "lockout_RAP": [...],
      "prog_RAP": [...],
      "my_custom_profile": [
        {
          "domain": "IPC::FUS",
          "register": "CPU0",
          "ssid": "U1.U5",
          "tname_patterns": ["YOUR_PATTERN_HERE"]
        }
      ]
    }
  }
}
```

3. Set `active_mapping` to your profile name
4. Run the tool!

---

## 📖 Full Documentation

See `docs/ITF_SSID_MAPPING.md` for:
- Complete mapping reference
- Pattern matching examples
- Troubleshooting guide
- Migration instructions

---

## ⚠️ Important Notes

- **Backward Compatible**: Existing functionality unchanged
- **No Code Changes**: Python files remain the same
- **Validation**: Tool warns if mapping not found
- **JSON Format**: Must be valid JSON (check with jsonlint.com)

---

## 🔍 Quick Test

Test configuration loading:
```bash
py -3.14 -c "from src.parsers.itf_parser import ITFParser; ITFParser()"
```

Expected output:
```
📋 Loaded 9 SSID mappings for profile: lockout_RAP
```

---

## 💡 Pro Tips

1. **Keep Backup**: Save original config.json before editing
2. **Validate JSON**: Use online validators before running
3. **Version Control**: Commit config changes separately
4. **Documentation**: Add comments in JSON (use separate doc file)
5. **Testing**: Test with small dataset first

---

## 🎓 Example Workflow

### Scenario: Switch from lockout_RAP to prog_RAP

**Step 1**: Open `config.json`

**Step 2**: Find the line:
```json
"active_mapping": "lockout_RAP",
```

**Step 3**: Change to:
```json
"active_mapping": "prog_RAP",
```

**Step 4**: Save file

**Step 5**: Run your normal command:
```bash
py -3.14 -m src.main "I:/fuse/..." output -ituff .\input\
```

**Step 6**: Verify output shows:
```
📋 Loaded 9 SSID mappings for profile: prog_RAP
```

Done! ✅

---

## 📞 Support

For detailed information:
- **Full Guide**: `docs/ITF_SSID_MAPPING.md`
- **Config Documentation**: `docs/IMPROVEMENTS.md`
- **Usage Examples**: `docs/USAGE_EXAMPLES.md`
