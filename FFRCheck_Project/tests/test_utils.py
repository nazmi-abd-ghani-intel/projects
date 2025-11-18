"""Example unit tests for FFRCheck utilities"""

import pytest
from pathlib import Path
from src.utils.config import Config
from src.utils.performance import (
    safe_int_conversion,
    safe_float_conversion,
    format_file_size,
    format_duration
)
from src.utils.helpers import binary_to_hex_fast


class TestConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration loading."""
        config = Config()
        assert config.get('processing.chunk_size') == 10000
        assert config.get('processing.memory_optimization') is True
    
    def test_config_get_with_default(self):
        """Test getting config with default value."""
        config = Config()
        assert config.get('nonexistent.key', 'default') == 'default'
    
    def test_config_set(self):
        """Test setting configuration values."""
        config = Config()
        config.set('custom.value', 42)
        assert config.get('custom.value') == 42


class TestPerformanceUtils:
    """Test performance utility functions."""
    
    def test_safe_int_conversion_valid(self):
        """Test safe integer conversion with valid input."""
        assert safe_int_conversion('42') == 42
        assert safe_int_conversion(42) == 42
        assert safe_int_conversion(42.9) == 42
    
    def test_safe_int_conversion_invalid(self):
        """Test safe integer conversion with invalid input."""
        assert safe_int_conversion('invalid') == 0
        assert safe_int_conversion(None) == 0
        assert safe_int_conversion('invalid', default=999) == 999
    
    def test_safe_float_conversion_valid(self):
        """Test safe float conversion with valid input."""
        assert safe_float_conversion('42.5') == 42.5
        assert safe_float_conversion(42) == 42.0
    
    def test_safe_float_conversion_invalid(self):
        """Test safe float conversion with invalid input."""
        assert safe_float_conversion('invalid') == 0.0
        assert safe_float_conversion(None, default=99.9) == 99.9
    
    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(500) == "500.00 B"
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3600) == "1h 0m"
        assert format_duration(3665) == "1h 1m"


class TestHelpers:
    """Test helper functions."""
    
    def test_binary_to_hex_fast(self):
        """Test binary to hex conversion."""
        assert binary_to_hex_fast('1111') == 'F'
        assert binary_to_hex_fast('10101010') == 'AA'
        assert binary_to_hex_fast('11111111') == 'FF'
        assert binary_to_hex_fast('00000000') == '00'
    
    def test_binary_to_hex_fast_padding(self):
        """Test binary to hex with padding."""
        assert binary_to_hex_fast('1') == '1'
        assert binary_to_hex_fast('10') == '2'
        assert binary_to_hex_fast('100') == '4'


# To run tests:
# pytest tests/test_utils.py -v
# pytest tests/test_utils.py -v --cov=src.utils
