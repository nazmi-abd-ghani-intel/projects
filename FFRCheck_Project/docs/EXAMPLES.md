# Example Usage Scenarios

## Basic Usage

### Process XML and JSON files only

```bash
python -m src.main C:\input\folder C:\output\folder
```

This will:
- Parse `MTL_OLF.xml` from the input folder
- Parse `fuseDef.json` from the input folder
- Generate matched CSV reports
- Create HTML statistics report

## Advanced Usage

### 1. With UBE File

```bash
python -m src.main C:\input\folder C:\output\folder -ube C:\path\to\ube_file.txt
```

Adds UBE data processing and generates unit data check reports.

### 2. With Specific QDF

```bash
python -m src.main C:\input\folder C:\output\folder -sspec L0V8
```

Processes sspec.txt for the L0V8 QDF only.

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
python -m src.main C:\input\folder C:\output\folder -mtlolf C:\custom\path\MTL_OLF.xml
```

Uses a MTL_OLF.xml file from a custom location.

### 6. With ITF Directory

```bash
python -m src.main C:\input\folder C:\output\folder -ituff C:\path\to\itf\files
```

Processes all ITF files in the specified directory.

### 7. With Console Logging

```bash
python -m src.main C:\input\folder C:\output\folder -log
```

Saves all console output to a log file in the output directory.

### 8. Complete Example (All Options)

```bash
python -m src.main ^
    C:\data\ffrcheck\input ^
    C:\data\ffrcheck\output ^
    -ube C:\data\ube_files\test_unit.txt ^
    -sspec "L0V8,L0VS" ^
    -mtlolf C:\data\MTL_OLF_v2.xml ^
    -ituff C:\data\itf_files ^
    -log ^
    --html-stats
```

This command:
- Processes XML and JSON from input directory
- Includes UBE data from custom location
- Processes sspec.txt for L0V8 and L0VS QDFs
- Uses custom MTL_OLF.xml location
- Processes ITF files from specified directory
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
├── _MTL_OLF-fuseDef.csv                      # Parsed XML data
├── _FUSEDEF-fuseDef.csv                      # Parsed JSON data
├── xfuse-mtlolf-check_fuseDef.csv            # Matched data
├── xfuse-dff-unitData-check_fuseDef.csv      # Unit data check (if -ube)
├── xsplit-sspec_L0V8_fuseDef.csv             # sspec breakdown (if -sspec)
├── _UBE-----<lotname>_<location>.csv         # UBE data (if -ube)
├── xstats_fuseDef.html                        # HTML report
└── xconsole_fuseDef.txt                       # Console log (if -log)
```

## Common Use Cases

### Use Case 1: Quick Validation
Check if XML and JSON files match:
```bash
python -m src.main .\input .\output
```

### Use Case 2: Full Analysis with Unit Data
Complete analysis including unit-level validation:
```bash
python -m src.main .\input .\output -ube .\data\ube.txt -log
```

### Use Case 3: QDF Exploration
Discover all QDFs and generate breakdown:
```bash
python -m src.main .\input .\output -sspec "*"
```

### Use Case 4: Targeted QDF Analysis
Focus on specific QDFs:
```bash
python -m src.main .\input .\output -sspec "L0V8,L0VS"
```

## Troubleshooting

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
3. fuseDef.json was successfully parsed

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
