"""Custom exception classes for FFRCheck"""


class FFRCheckError(Exception):
    """Base exception for FFRCheck errors."""
    pass


class FileNotFoundError(FFRCheckError):
    """Raised when a required file is not found."""
    pass


class ParseError(FFRCheckError):
    """Raised when parsing fails."""
    pass


class ValidationError(FFRCheckError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(FFRCheckError):
    """Raised when configuration is invalid."""
    pass


class ProcessingError(FFRCheckError):
    """Raised when processing fails."""
    pass


class DataIntegrityError(FFRCheckError):
    """Raised when data integrity checks fail."""
    pass
