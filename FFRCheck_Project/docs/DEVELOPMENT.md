# Development Guide

## Setting Up Development Environment

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Git (optional, for version control)

### Installation Steps

1. **Clone or navigate to the project directory**

```bash
cd C:\Users\nabdghan\Desktop\Code_Scripts\FFRCheck\FFRCheck_Project
```

2. **Create a virtual environment (recommended)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Install in development mode (optional)**

```bash
pip install -e .
```

## Project Structure for Developers

```
src/
├── parsers/          # Add new data parsers here
├── processors/       # Add new data processors here
└── utils/            # Add utility functions here
```

## Adding a New Parser

1. Create a new file in `src/parsers/` (e.g., `my_parser.py`)

```python
"""My Parser for custom data format"""

from typing import List, Dict, Any
from pathlib import Path


class MyParser:
    """Parses custom data format."""
    
    def __init__(self, sanitizer):
        self.sanitizer = sanitizer
    
    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse custom file format."""
        # Implementation here
        pass
```

2. Update `src/parsers/__init__.py`

```python
from .my_parser import MyParser

__all__ = [..., 'MyParser']
```

3. Integrate in `src/ffr_processor.py`

```python
from .parsers import MyParser

class FFRProcessor:
    def __init__(self, ...):
        # ...
        self.my_parser = MyParser(self.sanitizer)
```

## Adding a New Processor

1. Create a new file in `src/processors/` (e.g., `my_processor.py`)

```python
"""My Processor for custom operations"""

from typing import List, Dict, Any
from pathlib import Path


class MyProcessor:
    """Processes data in custom way."""
    
    def __init__(self, sanitizer, file_processor):
        self.sanitizer = sanitizer
        self.file_processor = file_processor
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process data."""
        # Implementation here
        pass
```

2. Update imports and integrate as needed

## Code Style Guidelines

### Naming Conventions

- **Classes**: PascalCase (e.g., `XMLParser`, `FFRProcessor`)
- **Functions/Methods**: snake_case (e.g., `parse_file`, `create_csv`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_BUFFER_SIZE`)
- **Private methods**: Prefix with underscore (e.g., `_internal_method`)

### Documentation

All modules, classes, and public functions should have docstrings:

```python
def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a file and extract data.
    
    Args:
        file_path: Path to the file to parse
        
    Returns:
        List of dictionaries containing parsed data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ParseError: If file format is invalid
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Any, Optional
from pathlib import Path

def process_data(data: List[Dict[str, Any]], 
                 output_path: Optional[Path] = None) -> bool:
    pass
```

## Error Handling

Always handle expected errors gracefully:

```python
try:
    data = parse_file(file_path)
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found")
    return []
except Exception as e:
    print(f"Unexpected error: {e}")
    return []
```

## Memory Optimization

For large file processing:

1. **Use generators instead of lists**

```python
def read_large_file(file_path: Path):
    with open(file_path) as f:
        for line in f:
            yield process_line(line)
```

2. **Stream CSV writing**

```python
def write_csv_streaming(data_generator, output_path):
    with open(output_path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data_generator:
            writer.writerow(row)
```

3. **Clear memory explicitly**

```python
element.clear()
while element.getprevious() is not None:
    del element.getparent()[0]
```

## Testing

### Manual Testing

1. Create a test input directory with sample files
2. Run the application with various options
3. Verify output files are generated correctly
4. Check console output and logs

Example test command:
```bash
python -m src.main .\test_data\input .\test_data\output -log
```

### Unit Testing (Future)

Create test files in a `tests/` directory:

```
tests/
├── __init__.py
├── test_xml_parser.py
├── test_json_parser.py
└── test_helpers.py
```

Example test:

```python
import unittest
from src.parsers import XMLParser
from src.utils import CSVSanitizer

class TestXMLParser(unittest.TestCase):
    def setUp(self):
        self.sanitizer = CSVSanitizer()
        self.parser = XMLParser(self.sanitizer)
    
    def test_parse_valid_xml(self):
        data = self.parser.parse_xml_optimized('test_files/valid.xml')
        self.assertIsNotNone(data)
        self.assertGreater(len(data), 0)
```

## Debugging

### Enable Console Logging

Always use `-log` flag during development:

```bash
python -m src.main .\input .\output -log
```

### Add Debug Print Statements

```python
print(f"Debug: Processing {len(data)} records")
print("-" * 60)
```

### Use Python Debugger

Add breakpoints in code:

```python
import pdb; pdb.set_trace()
```

## Performance Profiling

Use cProfile for performance analysis:

```bash
python -m cProfile -o profile.stats -m src.main .\input .\output
```

Analyze results:

```python
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)
```

## Common Development Tasks

### Adding a Command-Line Argument

Edit `src/main.py`:

```python
parser.add_argument('-myarg', '--myargument', 
                   help='My new argument description')
```

### Changing Output Format

Edit `src/processors/csv_processor.py` or create new processor

### Adding New Statistics

Edit `src/processors/html_stats.py`:

```python
def add_custom_stats(self, stats_data):
    self.stats_data['custom'] = stats_data
```

## Building and Distribution

### Create Distribution Package

```bash
python setup.py sdist bdist_wheel
```

### Install Package

```bash
pip install dist/ffrcheck-1.0.0-py3-none-any.whl
```

### Run Installed Package

```bash
ffrcheck .\input .\output -sspec L0V8
```

## Version Control

### Recommended .gitignore

Already included in project:
- Python cache files
- Virtual environments
- Output files (CSV, HTML, logs)
- IDE files

### Commit Messages

Use clear, descriptive commit messages:
```
Add support for wildcard QDF discovery
Fix memory leak in XML parser
Update documentation for new features
```

## Getting Help

- Review original script: `FFRCheck.py`
- Check documentation: `README.md`, `ARCHITECTURE.md`
- Review examples: `EXAMPLES.md`
- Add issues/questions in code comments
