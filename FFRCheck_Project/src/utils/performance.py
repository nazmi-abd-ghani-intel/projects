"""Performance and validation utilities"""

from typing import Any, Callable, Dict, List
import time
from functools import wraps


def timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        # Get function name and class if method
        func_name = func.__name__
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
            func_name = f"{class_name}.{func_name}"
        
        print(f"⏱️  {func_name} completed in {elapsed:.2f}s")
        return result
    
    return wrapper


def validate_file_exists(file_path: str, file_type: str = "File") -> bool:
    """
    Validate that a file exists.
    
    Args:
        file_path: Path to file
        file_type: Type description for error message
        
    Returns:
        True if file exists
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    from pathlib import Path
    from .exceptions import FileNotFoundError
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_type} not found: {file_path}")
    
    return True


def validate_dict_keys(data: Dict, required_keys: List[str], context: str = "Data") -> bool:
    """
    Validate that dictionary contains required keys.
    
    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        context: Context description for error message
        
    Returns:
        True if all keys present
        
    Raises:
        ValidationError: If required keys missing
    """
    from .exceptions import ValidationError
    
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        raise ValidationError(
            f"{context} missing required keys: {', '.join(missing_keys)}"
        )
    
    return True


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m"
