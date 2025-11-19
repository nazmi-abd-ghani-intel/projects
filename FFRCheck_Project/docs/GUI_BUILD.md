# FFR Check GUI Application - Build Instructions

## Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

## Building the Executable

### Option 1: Using the spec file (Recommended)
```bash
pyinstaller gui_app.spec
```

### Option 2: Simple one-line command
```bash
pyinstaller --name=FFRCheck --windowed --onedir --add-data "config.json;." --add-data "FleFuseSettings.json;." --add-data "src;src" gui_app.py
```

### Option 3: Console-enabled version (for debugging)
```bash
pyinstaller --name=FFRCheck --onedir --add-data "config.json;." --add-data "FleFuseSettings.json;." --add-data "src;src" gui_app.py
```

## Output

The executable will be created in the `dist/FFRCheck/` directory:
- `dist/FFRCheck/FFRCheck.exe` - Main executable
- `dist/FFRCheck/` - Contains all dependencies and data files

## Distribution

To distribute the application:
1. Zip the entire `dist/FFRCheck/` folder
2. Users can extract and run `FFRCheck.exe` directly
3. No Python installation required on user machines

## Running the GUI

### From Python (Development):
```bash
python gui_app.py
```

### From Executable (Production):
```bash
dist\FFRCheck\FFRCheck.exe
```

## Features

### Required Arguments:
- **Input Directory**: Directory containing fuseDef.json and source files
- **Output Directory**: Directory for generated CSV and HTML reports

### Optional Arguments:
- **SSPEC (QDF)**: QDF specification (e.g., L15H or L0V8,L0VS,L15E or *)
- **UBE File**: Path to UBE file for UBE processing
- **MTL_OLF.xml**: Path to MTL_OLF.xml file (defaults to input_dir/MTL_OLF.xml)
- **ITF Directory**: Directory containing .itf, .txt, or .itf.gz files
- **VisualID Filter**: Filter by specific visualID(s) (e.g., U538G05900011,U538G09400164)

### Options:
- **Enable Console Logging**: Save console output to log file
- **Generate HTML Statistics Report**: Create interactive HTML report

### Buttons:
- **Run FFR Check**: Start the processing
- **Stop**: Terminate the running process
- **Clear Output**: Clear the output console
- **Open Output Folder**: Open the output directory in File Explorer

## GUI Features

1. **Browse Buttons**: Easy file/folder selection
2. **Real-time Output**: See processing progress in real-time
3. **Status Bar**: Shows current status (Ready, Running, Completed, etc.)
4. **Config Integration**: Loads default values from config.json
5. **Thread-safe**: Responsive UI during processing
6. **Error Handling**: Clear error messages and validation

## Troubleshooting

### Build Issues:

**Issue**: ModuleNotFoundError during build
```bash
# Solution: Install missing packages
pip install -r requirements.txt
```

**Issue**: Data files not included
```bash
# Solution: Check that config.json and src/ folder exist
# Rebuild with --add-data flags
```

### Runtime Issues:

**Issue**: Config not found
```bash
# Solution: Ensure config.json is in the same directory as FFRCheck.exe
```

**Issue**: Python module errors
```bash
# Solution: Rebuild with --hidden-import flags for missing modules
pyinstaller --hidden-import=MODULE_NAME gui_app.spec
```

## File Structure After Build

```
dist/
└── FFRCheck/
    ├── FFRCheck.exe          # Main executable
    ├── config.json           # Configuration file
    ├── FleFuseSettings.json  # FLE settings
    ├── src/                  # Source code modules
    ├── docs/                 # Documentation
    └── _internal/            # PyInstaller dependencies
```

## Notes

- The executable includes the Python interpreter and all dependencies
- File size will be approximately 20-50 MB due to included dependencies
- First run may be slower as Windows verifies the executable
- Antivirus software may flag PyInstaller executables - this is normal for packed Python apps

## Advanced: Creating Single-File Executable

For a single .exe file (slower startup):
```bash
pyinstaller --name=FFRCheck --windowed --onefile --add-data "config.json;." --add-data "FleFuseSettings.json;." --add-data "src;src" gui_app.py
```

Note: Single-file executables extract to a temp folder on each run, which is slower than the onedir option.
