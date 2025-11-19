# FFR Check Project

A comprehensive tool for processing and analyzing FFR (Fuse Failure Rate) data from various sources including XML, JSON, UBE files, and sspec.txt files.

## Features

- **GUI Application**: User-friendly graphical interface with browse buttons and real-time output
- **XML Processing**: Parse MTL_OLF.xml files and extract token information with global_type support
- **JSON Processing**: Parse fuseDef.json files for fuse definitions
- **UBE Processing**: Parse UBE files for unit data
- **sspec Processing**: Parse sspec.txt files with wildcard QDF support
- **ITF Processing**: Process ITF (.itf, .itf.gz, .txt) files from directories
- **CSV Generation**: Generate multiple CSV reports with matching and validation
- **HTML Reports**: Generate interactive HTML statistics reports
- **Memory Optimization**: Efficient processing of large files
- **VisualID Filtering**: Filter ITF processing by specific visual IDs
- **Deterministic DFF Conversion**: Use global_type from XML for accurate format detection
- **Configuration System**: Centralized config.json for default settings

## Project Structure

```
FFRCheck_Project/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main entry point
│   ├── ffr_processor.py        # Core FFR processor
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── xml_parser.py       # XML parsing with global_type extraction
│   │   ├── json_parser.py      # JSON parsing logic
│   │   ├── ube_parser.py       # UBE parsing logic
│   │   ├── sspec_parser.py     # sspec parsing logic
│   │   └── itf_parser.py       # ITF parsing (.itf/.txt/.gz)
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── csv_processor.py    # CSV generation and processing
│   │   ├── html_stats.py       # HTML statistics generation
│   │   └── unit_data_sspec.py  # Unit data and StatusCheck logic
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py       # File I/O utilities
│       ├── sanitizer.py        # Data sanitization
│       └── helpers.py          # Helper functions (binary/hex conversion)
├── gui_app.py                  # GUI application (tkinter)
├── gui_app.spec                # PyInstaller build specification
├── build_gui.ps1               # Build automation script
├── config.json                 # Configuration file
├── FleFuseSettings.json        # FLE fuse settings
├── requirements.txt
├── setup.py
├── README.md
└── docs/
    ├── GUI_README.md           # GUI user guide
    ├── GUI_BUILD.md            # GUI build instructions
    └── ... (other documentation)
```

## Installation

```bash
# Clone or navigate to the project directory
cd FFRCheck_Project

# Install dependencies
pip install -r requirements.txt
```

## Usage

### GUI Application (Recommended)

```bash
# Run GUI application
python gui_app.py

# Or build standalone executable
.\build_gui.ps1
.\dist\FFRCheck\FFRCheck.exe
```

See [GUI_README.md](GUI_README.md) for detailed GUI usage.

### Command Line Interface

#### Basic Usage

```bash
python -m src.main <input_dir> <output_dir> -sspec <QDF>
```

#### Advanced Usage

```bash
# With UBE file and ITF directory
python -m src.main <input_dir> <output_dir> -sspec L15H -ube <ube_file> -ituff <itf_dir>

# With multiple QDFs
python -m src.main <input_dir> <output_dir> -sspec "L0V8,L0VS,L15E"

# Process all QDFs (wildcard)
python -m src.main <input_dir> <output_dir> -sspec "*"

# Filter by specific visual IDs
python -m src.main <input_dir> <output_dir> -sspec L15H -ituff <dir> -visualid "U123,U456"

# With custom MTL_OLF file
python -m src.main <input_dir> <output_dir> -sspec L15H -mtlolf <path_to_MTL_OLF.xml>

# Enable console logging
python -m src.main <input_dir> <output_dir> -sspec L15H -log

# Generate HTML statistics report (enabled by default)
python -m src.main <input_dir> <output_dir> -sspec L15H --html-stats
```

## Arguments

### Required
- `input_dir`: Input directory containing fuseDef.json and optionally sspec.txt
- `output_dir`: Output directory for generated CSV files
- `-sspec`: QDF specification(s) (e.g., L15H or L0V8,L0VS,L15E) or "*" for all QDFs [REQUIRED]

### Optional
- `-ube`: UBE file path to parse (enables DFF comparison)
- `-mtlolf`: MTL_OLF.xml file path (default: input_dir/MTL_OLF.xml)
- `-ituff`: Directory path containing ITF files (.itf/.txt/.itf.gz)
- `-visualid`: Comma-separated visual IDs to filter (e.g., "U123,U456" or "*" for all)
- `-log`: Enable console logging to file
- `--html-stats`: Generate interactive HTML statistics report (default: True)

See [CONFIG_ARGUMENTS.md](docs/CONFIG_ARGUMENTS.md) for detailed configuration options.

## Output Files

The tool generates several CSV files:

### Input Reports (I_Report_*)
1. `I_Report_MTL_OLF_<fusefilename>.csv` - Parsed MTL_OLF data with **global_type_MTL** column
2. `I_Report_FuseDef_<fusefilename>.csv` - Parsed fuseDef data
3. `I_Report_UBE_<lotname>_<location>.csv` - Parsed UBE data (if -ube provided)

### Validation Reports (V_Report_*)
4. `V_Report_FuseDef_vs_MTL_OLF_<fusefilename>.csv` - Combined matching results
5. `V_Report_DFF_UnitData_<fusefilename>.csv` - DFF unit data check with **global_type_MTL** column

### SSPEC Reports (S_*)
6. `S_SSPEC_Breakdown_<qdf>_<fusefilename>.csv` - sspec breakdown by QDF
7. `S_UnitData_by_Fuse_<qdf>_<fusefilename>.csv` - Unit data with **StatusCheck** (uses global_type for DFF conversion)

### ITF Reports
8. `ITF_Rows_<fusefilename>_<lotname>.csv` - ITF individual rows
9. `ITF_FullString_<fusefilename>_<lotname>.csv` - ITF fullstring data

### Other Reports
10. `HTML_Statistics_Report_<fusefilename>.html` - Interactive HTML statistics report
11. Console log file (if -log enabled)

**New in latest version:**
- `global_type_MTL` column shows data type (STRING/INTEGER/BINARY/HEX) for deterministic DFF conversion
- StatusCheck uses global_type for accurate dynamic/static/mismatch detection

## Requirements

- Python 3.7+
- lxml
- (other dependencies as needed)

## License

Internal Intel Tool

## Author

Original script by nabdghan
