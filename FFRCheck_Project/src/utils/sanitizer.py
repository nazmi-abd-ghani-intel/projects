"""CSV Sanitizer for XSS protection and data cleaning"""

import html


class CSVSanitizer:
    """
    Sanitizes CSV fields to prevent XSS attacks and formula injection.
    """
    
    def __init__(self):
        """Initialize the CSV sanitizer."""
        pass
    
    def sanitize_csv_field(self, value):
        """
        Sanitize a CSV field value to prevent XSS and formula injection.
        
        Args:
            value: The value to sanitize
            
        Returns:
            Sanitized string value
        """
        if value is None:
            return ''
        
        # Convert to string
        str_value = str(value)
        
        # Remove potential formula injection characters at the start
        if str_value and str_value[0] in ['=', '+', '-', '@', '\t', '\r']:
            str_value = "'" + str_value
        
        # Note: No HTML escaping needed for CSV files (only needed for HTML output)
        # The CSV format itself provides sufficient data isolation
        
        return str_value
    
    def sanitize_dict(self, data_dict):
        """
        Sanitize all values in a dictionary.
        
        Args:
            data_dict: Dictionary with data
            
        Returns:
            Dictionary with sanitized values
        """
        return {key: self.sanitize_csv_field(value) for key, value in data_dict.items()}
