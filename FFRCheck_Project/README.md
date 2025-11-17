# FFR Check Project

A comprehensive tool for processing and analyzing FFR (Fuse Failure Rate) data from various sources including XML, JSON, UBE files, and sspec.txt files.

## Features

- **XML Processing**: Parse MTL_OLF.xml files and extract token information
- **JSON Processing**: Parse fuseDef.json files for fuse definitions
- **UBE Processing**: Parse UBE files for unit data
- **sspec Processing**: Parse sspec.txt files with wildcard QDF support
- **ITF Processing**: Process ITF files from directories
- **CSV Generation**: Generate multiple CSV reports with matching and validation
- **HTML Reports**: Generate interactive HTML statistics reports
- **Memory Optimization**: Efficient processing of large files

## Project Structure

```
FFRCheck_Project/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main entry point
│   ├── ffr_processor.py        # Core FFR processor
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── xml_parser.py       # XML parsing logic
│   │   ├── json_parser.py      # JSON parsing logic
│   │   ├── ube_parser.py       # UBE parsing logic
│   │   ├── sspec_parser.py     # sspec parsing logic
│   │   └── itf_parser.py       # ITF parsing logic
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── csv_processor.py    # CSV generation and processing
│   │   └── html_stats.py       # HTML statistics generation
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py       # File I/O utilities
│       ├── sanitizer.py        # Data sanitization
│       └── helpers.py          # Helper functions
├── requirements.txt
├── setup.py
└── README.md
```

## Installation

```bash
# Clone or navigate to the project directory
cd FFRCheck_Project

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python -m src.main <input_dir> <output_dir>
```

### Advanced Usage

```bash
# With UBE file
python -m src.main <input_dir> <output_dir> -ube <ube_file_path>

# With specific QDF
python -m src.main <input_dir> <output_dir> -sspec L0V8

# With multiple QDFs
python -m src.main <input_dir> <output_dir> -sspec "L0V8,L0VS,L15E"

# Process all QDFs (wildcard)
python -m src.main <input_dir> <output_dir> -sspec "*"

# With ITF directory
python -m src.main <input_dir> <output_dir> -ituff <itf_directory>

# With custom MTL_OLF file
python -m src.main <input_dir> <output_dir> -mtlolf <path_to_MTL_OLF.xml>

# Enable console logging
python -m src.main <input_dir> <output_dir> -log

# Generate HTML statistics report
python -m src.main <input_dir> <output_dir> --html-stats
```

## Arguments

- `input_dir`: Input directory containing fuseDef.json and optionally sspec.txt
- `output_dir`: Output directory for generated CSV files
- `-sspec`: QDF specification(s) (e.g., L0V8 or L0V8,L0VS,L15E) or "*" for all QDFs
- `-ube`: UBE file path to parse
- `-mtlolf`: MTL_OLF.xml file path (if not in input directory)
- `-ituff`: Directory path containing ITF files to parse
- `-log`: Enable console logging to file
- `--html-stats`: Generate interactive HTML statistics report (default: True)

## Output Files

The tool generates several CSV files:

1. `_MTL_OLF-<fusefilename>.csv` - Parsed MTL_OLF data
2. `_FUSEDEF-<fusefilename>.csv` - Parsed fuseDef data
3. `xfuse-mtlolf-check_<fusefilename>.csv` - Combined matching results
4. `xfuse-dff-unitData-check_<fusefilename>.csv` - DFF unit data check
5. `xsplit-sspec_<qdf>_<fusefilename>.csv` - sspec breakdown (if -sspec is provided)
6. `_UBE-----<lotname>_<location>.csv` - Parsed UBE data (if -ube is provided)
7. `xconsole_<fusefilename>.txt` - Console log (if -log is enabled)
8. `xstats_<fusefilename>.html` - Interactive HTML statistics report

## Requirements

- Python 3.7+
- lxml
- (other dependencies as needed)

## License

Internal Intel Tool

## Author

Original script by nabdghan
