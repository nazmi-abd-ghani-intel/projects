"""Example integration of new utilities into existing code"""

# Example 1: Using Configuration
# =============================
# Before:
# fle_file = self.input_dir / "FleFuseSettings.json"
#
# After:
from src.utils import get_config

config = get_config()
fle_file = self.input_dir / config.get('fle_settings.filename')


# Example 2: Using Logger Instead of Print
# =========================================
# Before:
# print(f"✅ Created: {output_file.name}")
# print(f"⚠️  Warning: Missing data")
# print(f"❌ Error: {error_message}")
#
# After:
from src.utils import get_logger

logger = get_logger(__name__)
logger.info(f"✅ Created: {output_file.name}")
logger.warning(f"⚠️  Warning: Missing data")
logger.error(f"❌ Error: {error_message}")


# Example 3: Using Performance Decorator
# =======================================
# Before:
# def create_unit_data_sspec_csv(self, ...):
#     # ... processing logic
#     pass
#
# After:
from src.utils.performance import timing_decorator

@timing_decorator
def create_unit_data_sspec_csv(self, ...):
    # ... processing logic
    pass
# Output: ⏱️  UnitDataSspecProcessor.create_unit_data_sspec_csv completed in 2.34s


# Example 4: Using Custom Exceptions
# ===================================
# Before:
# if not file_path.exists():
#     print(f"Error: File not found: {file_path}")
#     return False
#
# After:
from src.utils.exceptions import FileNotFoundError

if not file_path.exists():
    raise FileNotFoundError(f"Required file not found: {file_path}")


# Example 5: Safe Type Conversions
# =================================
# Before:
# try:
#     value = int(data.get('field', 0))
# except (ValueError, TypeError):
#     value = 0
#
# After:
from src.utils.performance import safe_int_conversion

value = safe_int_conversion(data.get('field'), default=0)


# Example 6: Human-Readable Formatting
# =====================================
# Before:
# size_kb = file_size / 1024
# print(f"File size: {size_kb:.2f} KB")
#
# After:
from src.utils.performance import format_file_size

print(f"File size: {format_file_size(file_size)}")


# Example 7: Configuration in Main Script
# ========================================
# In src/main.py, you can add:
from src.utils import get_config, setup_logger
from pathlib import Path

def main():
    # Setup logging if -log argument provided
    if args.log:
        log_file = Path(args.output_dir) / f"ffr_check_{timestamp}.log"
        logger = setup_logger("FFRCheck", log_file=log_file)
        logger.info("FFR Check started")
    
    # Load configuration
    config = get_config()
    
    # Use config values
    chunk_size = config.get('processing.chunk_size')
    # ... rest of code


# Example 8: Error Handling with Custom Exceptions
# =================================================
# In your processor classes:
from src.utils.exceptions import ParseError, ValidationError

def parse_data(self, file_path):
    try:
        # ... parsing logic
        if not self._validate_data(data):
            raise ValidationError("Invalid data format")
    except Exception as e:
        raise ParseError(f"Failed to parse {file_path}: {e}")


# Example 9: Complete Integration Example
# ========================================
"""
Example of fully integrated unit_data_sspec.py with new utilities
"""
from pathlib import Path
from typing import Dict, List
from ..utils import get_config, get_logger
from ..utils.performance import timing_decorator, format_file_size
from ..utils.exceptions import FileNotFoundError, ValidationError

class UnitDataSspecProcessor:
    """Process unit data from ITF and map to SSPEC breakdown."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
    
    @timing_decorator
    def create_unit_data_sspec_csv(self, sspec_file, itf_file, output_file, qdf, dff_file=None, input_dir=None):
        """Create S_UnitData_by_Fuse CSV file with ITF and DFF data."""
        
        # Validate inputs
        if not sspec_file.exists():
            raise FileNotFoundError(f"SSPEC file not found: {sspec_file}")
        
        self.logger.info(f"🔄 Creating S_UnitData_by_Fuse for QDF '{qdf}'...")
        
        # Load FLE settings using config
        fle_filename = self.config.get('fle_settings.filename')
        fle_file = input_dir / fle_filename if input_dir else Path(fle_filename)
        
        if fle_file.exists():
            fle_fuses = self._load_fle_settings(fle_file)
            self.logger.info(f"Loaded {len(fle_fuses)} FLE fuses from {fle_filename}")
        
        # ... rest of processing
        
        self.logger.info(f"✅ Created: {output_file.name} ({len(processed_rows)} rows)")
        self.logger.info(f"   File size: {format_file_size(output_file.stat().st_size)}")
        
        return True


# Example 10: Testing Your Code
# ==============================
"""
Run tests with pytest:
    pytest tests/test_utils.py -v
    pytest tests/test_utils.py -v --cov=src.utils
"""
