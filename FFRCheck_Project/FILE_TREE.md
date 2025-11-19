# Project File Tree

```
FFRCheck_Project/
│
├── 📄 .gitignore                      # Git ignore patterns
├── 📄 README.md                       # Main project documentation
├── 📄 QUICKSTART.md                   # Quick start guide
├── 📄 PROJECT_SUMMARY.md              # Project creation summary
├── 📄 GUI_README.md                   # GUI user documentation
├── 📄 requirements.txt                # Python dependencies
├── 📄 setup.py                        # Package installation setup
├── 📄 config.json                     # Configuration settings
├── 📄 FleFuseSettings.json            # FLE fuse settings
├── 📄 gui_app.py                      # GUI application (tkinter)
├── 📄 gui_app.spec                    # PyInstaller build spec
├── 📄 build_gui.ps1                   # GUI build automation
│
├── 📁 docs/                           # Documentation directory
│   ├── 📄 ARCHITECTURE.md             # Technical architecture guide
│   ├── 📄 DEVELOPMENT.md              # Developer guide
│   ├── 📄 EXAMPLES.md                 # Usage examples
│   ├── 📄 CONFIG_ARGUMENTS.md         # Configuration documentation
│   ├── 📄 CONFIG_QUICKSTART.md        # Config quick start
│   ├── 📄 ITF_SSID_MAPPING.md         # ITF SSID mapping guide
│   ├── 📄 SSID_MAPPING_QUICKSTART.md  # SSID mapping quick start
│   ├── 📄 UNIT_DATA_SSPEC.md          # Unit data documentation
│   ├── 📄 USAGE_EXAMPLES.md           # Usage examples
│   ├── 📄 GUI_BUILD.md                # GUI build instructions
│   └── 📄 IMPROVEMENTS.md             # Changelog and improvements
│
└── 📁 src/                            # Source code directory
    ├── 📄 __init__.py                 # Package initialization
    ├── 📄 main.py                     # Main entry point & CLI
    ├── 📄 ffr_processor.py            # Core FFR processor
    │
    ├── 📁 parsers/                    # Data parsers
    │   ├── 📄 __init__.py             # Parser package init
    │   ├── 📄 xml_parser.py           # MTL_OLF.xml parser (✅ global_type)
    │   ├── 📄 json_parser.py          # fuseDef.json parser (✅ Complete)
    │   ├── 📄 ube_parser.py           # UBE file parser (✅ Complete)
    │   ├── 📄 sspec_parser.py         # sspec.txt parser (✅ Complete)
    │   └── 📄 itf_parser.py           # ITF parser (✅ .itf/.txt/.gz)
    │
    ├── 📁 processors/                 # Data processors
    │   ├── 📄 __init__.py             # Processor package init
    │   ├── 📄 csv_processor.py        # CSV generation (✅ global_type)
    │   ├── 📄 html_stats.py           # HTML report gen (✅ Complete)
    │   └── 📄 unit_data_sspec.py      # Unit data & StatusCheck (✅ Complete)
    │
    └── 📁 utils/                      # Utility modules
        ├── 📄 __init__.py             # Utils package init
        ├── 📄 file_utils.py           # File I/O utilities (✅ Complete)
        ├── 📄 sanitizer.py            # Data sanitization (✅ Complete)
        └── 📄 helpers.py              # Helper functions (✅ binary_to_hex)
```

## File Statistics

**Total Files:** 36+

**By Category:**
- Documentation: 12 files
- Source Code: 18 files
- Configuration: 3 files
- GUI Application: 3 files

**Implementation Status:**
- ✅ Fully Implemented: 18 files
- 📝 Documentation: 12 files
- ⚙️ Configuration: 3 files
- 🖥️ GUI: 3 files

## Recent Additions

### GUI Application
- `gui_app.py` - Full-featured tkinter GUI
- `gui_app.spec` - PyInstaller build configuration
- `build_gui.ps1` - Automated build script

### global_type Support
- XML parser extracts global_type from MTL_OLF.xml
- CSV processors include global_type_MTL column
- Deterministic DFF format conversion (BINARY/INTEGER/HEX/STRING)

### Enhanced Features
- ITF processing supports .itf, .txt, .itf.gz formats
- VisualID filtering for targeted analysis
- Configuration system with config.json

## Quick Navigation

### Start Here
1. `QUICKSTART.md` - For immediate usage
2. `README.md` - For overview and setup

### Documentation
- `docs/EXAMPLES.md` - See usage examples
- `docs/ARCHITECTURE.md` - Understand the design
- `docs/DEVELOPMENT.md` - For developers

### Source Code Entry Points
- `src/main.py` - Command-line interface
- `src/ffr_processor.py` - Main processing logic
- `src/parsers/` - Data parsing modules
- `src/processors/` - Data processing modules
- `src/utils/` - Utility functions

### Configuration
- `requirements.txt` - Install dependencies
- `setup.py` - Package installation
- `.gitignore` - Version control config
