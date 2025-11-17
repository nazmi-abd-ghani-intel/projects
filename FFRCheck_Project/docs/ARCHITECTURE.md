# FFR Check - Project Architecture

## Overview

FFRCheck is a modular Python application designed to process and analyze fuse failure rate data from multiple sources. The project is structured to be maintainable, testable, and extensible.

## Directory Structure

```
FFRCheck_Project/
├── src/                           # Source code
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # Main entry point
│   ├── ffr_processor.py          # Core orchestration logic
│   ├── parsers/                  # Data parsers
│   │   ├── __init__.py
│   │   ├── xml_parser.py         # MTL_OLF.xml parser
│   │   ├── json_parser.py        # fuseDef.json parser
│   │   ├── ube_parser.py         # UBE file parser
│   │   ├── sspec_parser.py       # sspec.txt parser
│   │   └── itf_parser.py         # ITF file parser
│   ├── processors/               # Data processors
│   │   ├── __init__.py
│   │   ├── csv_processor.py      # CSV generation and processing
│   │   └── html_stats.py         # HTML report generation
│   └── utils/                    # Utility modules
│       ├── __init__.py
│       ├── file_utils.py         # File I/O operations
│       ├── sanitizer.py          # Data sanitization
│       └── helpers.py            # Helper functions
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── .gitignore                    # Git ignore patterns
└── README.md                     # Project documentation
```

## Module Responsibilities

### Core Modules

#### `main.py`
- Command-line argument parsing
- Application initialization
- Console logging setup
- Workflow orchestration

#### `ffr_processor.py`
- Central coordinator for all operations
- Manages parsers and processors
- Handles QDF resolution
- Generates output filenames

### Parsers

#### `xml_parser.py`
- Parses MTL_OLF.xml files using lxml
- Extracts token information
- Handles fuse name/register pairing
- Uses iterparse for memory efficiency

#### `json_parser.py`
- Parses fuseDef.json files
- Extracts register and fuse definitions
- Formats address arrays

#### `ube_parser.py`
- Parses UBE (Unit Board) data files
- Extracts lot name and location information
- Processes unit-level test data

#### `sspec_parser.py`
- Parses sspec.txt files
- Supports wildcard QDF discovery
- Filters by target QDF set
- Streams large files efficiently

#### `itf_parser.py`
- Processes ITF (Intel Test Format) files
- Handles directory scanning
- Generates ITF-specific CSV outputs

### Processors

#### `csv_processor.py`
- Generates various CSV reports
- Performs data matching and validation
- Tracks mismatches and statistics
- Streams output for memory efficiency

#### `html_stats.py`
- Generates interactive HTML reports
- Creates statistical visualizations
- Provides breakdown tables
- Includes responsive styling

### Utilities

#### `file_utils.py`
- `FileProcessor`: Handles efficient file I/O
  - Streaming reads/writes
  - CSV processing
  - Large file handling
- `ConsoleLogger`: Context manager for logging
  - Tees output to file and console
  - Automatic cleanup

#### `sanitizer.py`
- `CSVSanitizer`: XSS and injection protection
  - HTML escaping
  - Formula injection prevention
  - Safe CSV field generation

#### `helpers.py`
- `binary_to_hex_fast()`: Binary to hex conversion
- `breakdown_fuse_string_fast()`: Fuse bit extraction
- `analyze_fuse_string_bits()`: Bit statistics
- `get_register_fuse_string()`: Lookup helper

## Data Flow

```
Input Files
    ├── MTL_OLF.xml ──┐
    ├── fuseDef.json ─┤
    ├── UBE files ────┼──> FFRProcessor ──> CSV Reports
    ├── sspec.txt ────┤                    HTML Report
    └── ITF files ────┘
```

### Processing Steps

1. **Initialization**
   - Parse command-line arguments
   - Create output directory
   - Initialize processors

2. **Data Parsing**
   - XML: Extract token information
   - JSON: Extract fuse definitions
   - UBE: Extract unit data (optional)
   - sspec: Extract fuse strings for QDFs (optional)
   - ITF: Process test files (optional)

3. **Data Processing**
   - Match XML and JSON data
   - Generate comparison reports
   - Calculate statistics
   - Track mismatches

4. **Output Generation**
   - Write CSV reports
   - Generate HTML statistics
   - Save console logs (optional)

## Memory Optimization

The application uses several techniques to handle large files efficiently:

1. **Streaming Parsing**: Uses generators and iterparse
2. **Chunk Processing**: Processes data in manageable chunks
3. **Lazy Loading**: Loads data only when needed
4. **Memory Cleanup**: Explicit cleanup after processing

## Extension Points

To add new functionality:

1. **New Parser**: Create a new parser in `src/parsers/`
2. **New Processor**: Create a new processor in `src/processors/`
3. **New Utility**: Add functions to appropriate utility module
4. **New Output Format**: Extend `csv_processor.py` or create new processor

## Error Handling

- File not found errors are caught and reported
- Parse errors include context information
- Processing continues even if optional components fail
- Console logging captures all output for debugging

## Testing Considerations

For future testing implementation:

1. **Unit Tests**: Test individual parsers and utilities
2. **Integration Tests**: Test complete workflows
3. **Performance Tests**: Validate memory efficiency
4. **Regression Tests**: Ensure output consistency

## Dependencies

- **lxml**: XML parsing with memory efficiency
- **pathlib**: Modern path handling
- **argparse**: Command-line interface
- **csv**: CSV file handling
- **json**: JSON parsing
- **html**: HTML escaping

## Configuration

The application is configured primarily through command-line arguments. Future enhancements could include:

- Configuration file support (YAML/JSON)
- Environment variable support
- Default settings management
