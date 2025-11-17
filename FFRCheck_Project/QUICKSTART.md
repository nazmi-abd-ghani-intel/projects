# Quick Start Guide

## Installation

```powershell
# Navigate to project directory
cd C:\Users\nabdghan\Desktop\Code_Scripts\FFRCheck\FFRCheck_Project

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

```powershell
# Run with minimal options (XML + JSON processing)
python -m src.main <input_folder> <output_folder>

# Example:
python -m src.main C:\data\input C:\data\output
```

## Common Commands

### Process with UBE file
```powershell
python -m src.main .\input .\output -ube C:\path\to\ube.txt
```

### Process specific QDF
```powershell
python -m src.main .\input .\output -sspec L0V8
```

### Process all QDFs (wildcard)
```powershell
python -m src.main .\input .\output -sspec "*"
```

### Enable logging
```powershell
python -m src.main .\input .\output -log
```

## Required Input Files

Place these files in your input directory:
- `fuseDef.json` (required)
- `MTL_OLF.xml` (required, or specify with -mtlolf)
- `sspec.txt` (optional, for -sspec)

## Output Files

The tool generates these files in the output directory:
- `_MTL_OLF-*.csv` - Parsed XML data
- `_FUSEDEF-*.csv` - Parsed JSON data  
- `xfuse-mtlolf-check_*.csv` - Matched comparison
- `xstats_*.html` - Interactive statistics report

## Getting Help

```powershell
python -m src.main --help
```

## Troubleshooting

**Problem**: "Invalid input directory"  
**Solution**: Verify the directory path exists and contains fuseDef.json

**Problem**: "MTL_OLF.xml not found"  
**Solution**: Use `-mtlolf` flag to specify custom location

**Problem**: No output generated  
**Solution**: Use `-log` flag to see detailed error messages

## Next Steps

- Read `README.md` for detailed documentation
- Check `docs/EXAMPLES.md` for more usage scenarios
- Review `docs/ARCHITECTURE.md` to understand the codebase
- See `docs/DEVELOPMENT.md` for development guidelines
