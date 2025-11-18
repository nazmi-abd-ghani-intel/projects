"""Configuration management for FFRCheck"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager with defaults and file loading."""
    
    # Default configuration
    DEFAULTS = {
        "fle_settings": {
            "filename": "FleFuseSettings.json",
            "description": "FLE (Fuse Lockout Enable) fuse settings configuration"
        },
        "processing": {
            "chunk_size": 10000,
            "progress_updates": 1000,
            "memory_optimization": True
        },
        "output": {
            "csv_delimiter": ",",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "decimal_places": 1
        },
        "html_report": {
            "max_table_rows": 100,
            "enable_excel_export": True,
            "theme": "default"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
    }
    
    def __init__(self, config_file: Path = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Optional path to configuration JSON file
        """
        self._config = self.DEFAULTS.copy()
        
        if config_file and config_file.exists():
            self.load(config_file)
    
    def load(self, config_file: Path):
        """
        Load configuration from JSON file.
        
        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                self._deep_update(self._config, user_config)
        except Exception as e:
            print(f"⚠️  Warning: Could not load config file {config_file}: {e}")
            print("   Using default configuration.")
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """
        Recursively update nested dictionary.
        
        Args:
            base_dict: Base dictionary to update
            update_dict: Dictionary with updates
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'processing.chunk_size')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'processing.chunk_size')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict:
        """
        Get full configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def save(self, config_file: Path):
        """
        Save configuration to JSON file.
        
        Args:
            config_file: Path to save configuration
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving config file {config_file}: {e}")


# Global configuration instance
_config = None


def get_config(config_file: Path = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Configuration instance
    """
    global _config
    
    if _config is None:
        # Try to load from default location
        if config_file is None:
            default_config = Path(__file__).parent.parent.parent / "config.json"
            if default_config.exists():
                config_file = default_config
        
        _config = Config(config_file)
    
    return _config
