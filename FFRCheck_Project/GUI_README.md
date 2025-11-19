# FFR Check GUI Application

A graphical user interface for the FFR Check (Fuse Fuse Register Checker) tool.

## Quick Start

### Running from Python:
```bash
python gui_app.py
```
or
```bash
py -3.14 gui_app.py
```

### Building Executable:
```bash
.\build_gui.ps1
```
or
```bash
pyinstaller gui_app.spec
```

## Features

### User-Friendly Interface
- **Browse Buttons**: Easy file and folder selection
- **Real-time Output**: See processing progress as it happens
- **Status Indicators**: Clear status bar showing current state
- **Config Integration**: Automatically loads defaults from config.json

### All FFR Check Features
- Process fuseDef.json, MTL_OLF.xml, UBE files, ITF files
- Support for .itf, .txt, and .itf.gz file formats
- Multiple QDF processing (L15H, L0V8,L0VS,L15E, or *)
- VisualID filtering for focused analysis
- HTML statistics report generation
- Console logging option

### Input Fields

#### Required:
- **Input Directory**: Directory containing fuseDef.json and source files

#### Optional:
- **Output Directory**: Where to save results (default: output)
- **SSPEC (QDF)**: QDF specification string
- **UBE File**: Path to UBE file
- **MTL_OLF.xml**: Path to MTL_OLF file
- **ITF Directory**: Folder containing ITF files
- **VisualID Filter**: Comma-separated list of visualIDs to process

#### Options:
- ☑ Enable Console Logging
- ☑ Generate HTML Statistics Report

### Buttons
- **Run FFR Check**: Start processing
- **Stop**: Terminate running process
- **Clear Output**: Clear the output console
- **Open Output Folder**: Open results folder in Explorer

## Building the Executable

### Prerequisites:
```bash
pip install pyinstaller
```

### Build Commands:

**Simple build (recommended):**
```bash
.\build_gui.ps1
```

**Manual build:**
```bash
pyinstaller gui_app.spec
```

**With console window (for debugging):**
```bash
pyinstaller gui_app.spec --console
```

### Output:
```
dist/FFRCheck/
├── FFRCheck.exe          # Run this!
├── config.json           # Configuration
├── FleFuseSettings.json  # FLE settings
├── src/                  # Source modules
└── _internal/            # Dependencies
```

## Distribution

1. Build the executable using the build script
2. Zip the entire `dist/FFRCheck` folder
3. Users can extract and run `FFRCheck.exe` directly
4. **No Python installation required** on user machines!

## Screenshots

### Main Window
The GUI provides an intuitive interface with:
- Clear input fields with browse buttons
- Optional arguments grouped logically
- Real-time output console
- Status bar for current operation

### Workflow
1. Browse and select input directory
2. Set optional parameters (SSPEC, UBE, ITF, etc.)
3. Click "Run FFR Check"
4. Watch real-time progress in output console
5. Click "Open Output Folder" to view results

## Configuration

The GUI automatically loads default values from `config.json`:
- Default paths
- Default QDF specifications
- Default options (logging, HTML generation)

Users can override these defaults through the GUI interface.

## Error Handling

The GUI provides clear error messages for:
- Missing required input directory
- File not found errors
- Processing errors
- Invalid configurations

## Performance

- **Multi-threaded**: UI remains responsive during processing
- **Real-time Updates**: See output as it's generated
- **Cancellable**: Stop button to terminate long-running processes

## Troubleshooting

### GUI Won't Start
```bash
# Check Python/tkinter installation
python -m tkinter
```

### Build Errors
```bash
# Install/update PyInstaller
pip install --upgrade pyinstaller

# Install all requirements
pip install -r requirements.txt
```

### Executable Errors
- Ensure config.json is in the same folder as FFRCheck.exe
- Check that all source files exist in the src/ folder
- Run with console window enabled to see error messages

## Technical Details

- **Framework**: tkinter (built into Python)
- **Packaging**: PyInstaller
- **Threading**: Uses threading module for async processing
- **IPC**: Queue-based communication for thread-safe UI updates
- **Process Management**: subprocess module for running FFR Check

## Requirements

### For running from source:
- Python 3.10+
- tkinter (usually included with Python)
- All FFR Check dependencies

### For running executable:
- Windows 10/11
- No Python installation needed!

## Development

### File Structure:
```
gui_app.py           # Main GUI application
gui_app.spec         # PyInstaller specification
build_gui.ps1        # Build script
docs/GUI_BUILD.md    # Detailed build instructions
```

### Modifying the GUI:
1. Edit `gui_app.py`
2. Test with `python gui_app.py`
3. Rebuild with `.\build_gui.ps1`

## License

Same as FFR Check main application.

## Support

For issues or questions about the GUI:
1. Check docs/GUI_BUILD.md for detailed instructions
2. Review error messages in output console
3. Enable console window in build for debugging

## Future Enhancements

Potential features for future versions:
- [ ] Profile management (save/load configurations)
- [ ] Batch processing multiple input directories
- [ ] Progress bar for long operations
- [ ] Recent files/folders dropdown
- [ ] Custom themes
- [ ] Results preview in GUI
- [ ] Configuration validation
- [ ] Drag-and-drop support
