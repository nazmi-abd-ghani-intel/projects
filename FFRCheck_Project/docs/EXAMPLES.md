# Example Usage Scenarios

## GUI Application (Recommended)

### Launch GUI
```bash
python gui_app.py
```

The GUI provides:
- Browse buttons for all file/folder selections
- Visual ID filtering with text input
- Real-time output console
- One-click execution

See [GUI_README.md](../GUI_README.md) for complete GUI documentation.

## Command Line Usage

### Process with Required Arguments

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L15H
```

**Note**: `-sspec` argument is now REQUIRED (previously optional).

This will:
- Parse `MTL_OLF.xml` from the input folder (extracts global_type)
- Parse `fuseDef.json` from the input folder
- Generate matched CSV reports with global_type_MTL columns
- Create HTML statistics report

## Advanced Usage

### 1. With UBE File (Enables DFF Comparison)

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L15H -ube C:\path\to\ube_file.ube
```

Adds UBE data processing and generates:
- `V_Report_DFF_UnitData_*.csv` with global_type_MTL column
- DFF comparison with deterministic format conversion (uses global_type)

### 2. With ITF Directory and Visual ID Filter

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L15H -ituff C:\itf\dir -visualid "U123,U456"
```

Processes ITF files (.itf/.txt/.itf.gz) for specific visual IDs only.

### 3. With Multiple QDFs

```bash
python -m src.main C:\input\folder C:\output\folder -sspec "L0V8,L0VS,L15E"
```

Processes sspec.txt for multiple specified QDFs.

### 4. With Wildcard (All QDFs)

```bash
python -m src.main C:\input\folder C:\output\folder -sspec "*"
```

Automatically discovers and processes all QDFs found in sspec.txt.

### 5. With Custom MTL_OLF Location

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L15H -mtlolf C:\custom\path\MTL_OLF.xml
```

Uses a MTL_OLF.xml file from a custom location.

### 6. With Console Logging

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L15H -log
```

Saves all console output to a log file in the output directory.

### 7. Complete Example (All Options)

```bash
python -m src.main ^
    C:\data\ffrcheck\input ^
    C:\data\ffrcheck\output ^
    -sspec "L0V8,L0VS" ^
    -ube C:\data\ube_files\test_unit.ube ^
    -mtlolf C:\data\MTL_OLF_v2.xml ^
    -ituff C:\data\itf_files ^
    -visualid "U123,U456,U789" ^
    -log ^
    --html-stats
```

This command:
- Processes XML (with global_type extraction) and JSON from input directory
- Includes UBE data with deterministic DFF format conversion
- Processes sspec.txt for L0V8 and L0VS QDFs
- Uses custom MTL_OLF.xml location
- Processes ITF files (.itf/.txt/.itf.gz) from specified directory
- Filters for specific visual IDs only
- Enables console logging
- Generates HTML statistics report

## Expected Input File Structure

Your input directory should contain:

```
input_folder/
├── fuseDef.json          # Required
├── MTL_OLF.xml          # Required (or specify with -mtlolf)
└── sspec.txt            # Optional (needed for -sspec)
```

## Expected Output Files

The tool generates files in the output directory:

```
output_folder/
├── I_Report_MTL_OLF_<fusefilename>.csv              # Parsed XML with global_type_MTL
├── I_Report_FuseDef_<fusefilename>.csv              # Parsed JSON data
├── I_Report_UBE_<lotname>_<location>.csv            # UBE data (if -ube)
├── V_Report_FuseDef_vs_MTL_OLF_<fusefilename>.csv   # Matched comparison
├── V_Report_DFF_UnitData_<fusefilename>.csv         # DFF check with global_type_MTL
├── S_SSPEC_Breakdown_<qdf>_<fusefilename>.csv       # sspec breakdown (if -sspec)
├── S_UnitData_by_Fuse_<qdf>_<fusefilename>.csv      # Unit data with StatusCheck
├── ITF_Rows_<fusefilename>_<lotname>.csv            # ITF rows (if -ituff)
├── ITF_FullString_<fusefilename>_<lotname>.csv      # ITF fullstring (if -ituff)
├── HTML_Statistics_Report_<fusefilename>.html        # Interactive HTML report
└── Console log (if -log)
```

**Key Features:**
- `global_type_MTL` column in I_Report_MTL_OLF and V_Report_DFF_UnitData
- StatusCheck uses global_type for deterministic DFF conversion (BINARY/INTEGER/HEX/STRING)
- ITF processing supports .itf, .txt, and .itf.gz formats

## Common Use Cases

### Use Case 1: GUI Quick Start (Easiest)
```bash
python gui_app.py
```
Use browse buttons, click Run, view results!

### Use Case 2: Quick Validation with Specific QDF
Check if XML and JSON files match for a specific QDF:
```bash
python -m src.main .\input .\output -sspec L15H
```

### Use Case 3: Full Analysis with Unit Data
Complete analysis including unit-level validation with DFF comparison:
```bash
python -m src.main .\input .\output -sspec L15H -ube .\data\ube.ube -ituff .\itf_dir -log
```

### Use Case 4: QDF Exploration
Discover all QDFs and generate breakdowns:
```bash
python -m src.main .\input .\output -sspec "*"
```

### Use Case 5: Targeted Visual ID Analysis
Focus on specific visual IDs:
```bash
python -m src.main .\input .\output -sspec L15H -ituff .\itf_dir -visualid "U123,U456"
```

### Use Case 6: Multiple QDFs with Filtering
Process multiple QDFs with visual ID filter:
```bash
python -m src.main .\input .\output -sspec "L0V8,L0VS" -ituff .\itf -visualid "*"
```

## Troubleshooting

### Error: "sspec argument is required"
The `-sspec` argument is now REQUIRED. Provide a QDF (e.g., `-sspec L15H`) or wildcard (`-sspec "*"`)

### Error: "Invalid input directory"
Ensure the directory exists and contains fuseDef.json

### Error: "MTL_OLF.xml not found"
Use -mtlolf to specify custom location or ensure file is in input directory

### Warning: "Cannot create combined CSV"
Both XML and JSON files must be successfully parsed

### No sspec output generated
Ensure:
1. sspec.txt exists in input directory
2. Target QDFs exist in sspec.txt
3. `-sspec` argument is provided

### ITF files not processed
Ensure:
1. `-ituff` points to directory with .itf, .txt, or .itf.gz files
2. ITF files have visualID fields
3. Check ITF_SSID_MAPPING.md for SSID configuration

### DFF conversion issues
Check `global_type_MTL` column in output CSVs to verify data type detection:
- BINARY: Binary string (e.g., "1111")
- INTEGER: Decimal number (e.g., "15")
- HEX: Hexadecimal (e.g., "F")
- STRING: Treated as hexadecimal

## Performance Tips

1. **Large sspec.txt files**: Use specific QDFs instead of wildcard
2. **Memory constraints**: Process files individually
3. **Enable logging**: Use -log flag for detailed debugging

## Integration with Other Tools

The CSV outputs can be imported into:
- Microsoft Excel for manual analysis
- Python pandas for further processing
- Database systems for storage and querying
- BI tools for visualization
