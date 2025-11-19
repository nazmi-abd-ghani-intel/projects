# Quick Start Guide

## Installation

```powershell
# Navigate to project directory
cd C:\git-repo\nabdghan-git\projects\FFRCheck_Project

# Install dependencies
pip install -r requirements.txt
```

## Quick Start Options

### Option 1: GUI Application (Easiest)

```powershell
# Run GUI
python gui_app.py

# Or build standalone executable
.\build_gui.ps1
.\dist\FFRCheck\FFRCheck.exe
```

**Benefits**: Browse buttons, real-time output, no command-line needed!

See [GUI_README.md](GUI_README.md) for detailed GUI usage.

### Option 2: Command Line

```powershell
# Basic command (requires -sspec)
python -m src.main <input_folder> <output_folder> -sspec <QDF>

# Example:
python -m src.main C:\data\input C:\data\output -sspec L15H
```

## Common Commands

### Process with UBE file (enables DFF comparison)
```powershell
python -m src.main .\input .\output -sspec L15H -ube C:\path\to\ube.txt
```

### Process with ITF directory
```powershell
python -m src.main .\input .\output -sspec L15H -ituff C:\path\to\itf_dir
```

### Filter by specific visual IDs
```powershell
python -m src.main .\input .\output -sspec L15H -ituff .\itf -visualid "U123,U456"
```

### Process multiple QDFs
```powershell
python -m src.main .\input .\output -sspec "L0V8,L0VS,L15E"
```

### Process all QDFs (wildcard)
```powershell
python -m src.main .\input .\output -sspec "*"
```

### Enable logging
```powershell
python -m src.main .\input .\output -sspec L15H -log
```

## Required Input Files

Place these files in your input directory:
- `fuseDef.json` (required)
- `MTL_OLF.xml` (required, or specify with -mtlolf)
- `sspec.txt` (required when using -sspec)

## Output Files

The tool generates these files in the output directory:

**Input Reports:**
- `I_Report_MTL_OLF_*.csv` - Parsed XML data with global_type_MTL column
- `I_Report_FuseDef_*.csv` - Parsed JSON data  
- `I_Report_UBE_*.csv` - Parsed UBE data (if -ube provided)

**Validation Reports:**
- `V_Report_FuseDef_vs_MTL_OLF_*.csv` - Matched comparison
- `V_Report_DFF_UnitData_*.csv` - DFF check with global_type_MTL column

**SSPEC Reports:**
- `S_SSPEC_Breakdown_*.csv` - SSPEC breakdown by QDF
- `S_UnitData_by_Fuse_*.csv` - Unit data with StatusCheck

**Other:**
- `HTML_Statistics_Report_*.html` - Interactive statistics report
- `ITF_*.csv` - ITF processing results (if -ituff provided)

## Getting Help

```powershell
python -m src.main --help
```

## Troubleshooting

**Problem**: "Invalid input directory"  
**Solution**: Verify the directory path exists and contains fuseDef.json

**Problem**: "MTL_OLF.xml not found"  
**Solution**: Use `-mtlolf` flag to specify custom location

**Problem**: "sspec argument is required"  
**Solution**: Provide `-sspec` with a QDF value (e.g., `-sspec L15H`)

**Problem**: No output generated  
**Solution**: Use `-log` flag to see detailed error messages

**Problem**: ITF files not processed  
**Solution**: Ensure -ituff points to directory with .itf, .txt, or .itf.gz files

## Next Steps

- Read `README.md` for detailed documentation
- Check `docs/EXAMPLES.md` for more usage scenarios
- Try `GUI_README.md` for GUI application guide
- See `docs/CONFIG_ARGUMENTS.md` for configuration options
- Review `docs/ARCHITECTURE.md` to understand the codebase
- See `docs/DEVELOPMENT.md` for development guidelines
