"""File processing utilities for efficient I/O operations"""

import sys
import csv
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional
from contextlib import contextmanager


class FileProcessor:
    """
    Handles efficient file reading and writing operations.
    """
    
    def __init__(self, chunk_size: int = 8192):
        """
        Initialize the file processor.
        
        Args:
            chunk_size: Size of chunks for streaming operations
        """
        self.chunk_size = chunk_size
    
    def read_file_lines(self, file_path: Path, encoding: str = 'utf-8') -> Generator[str, None, None]:
        """
        Read file lines as a generator for memory efficiency.
        
        Args:
            file_path: Path to the file
            encoding: File encoding
            
        Yields:
            Lines from the file
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                for line in f:
                    yield line.strip()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return
    
    def process_large_csv_generator(self, csv_file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """
        Process a large CSV file as a generator.
        
        Args:
            csv_file_path: Path to the CSV file
            
        Yields:
            Dictionary for each row
        """
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    yield row
        except Exception as e:
            print(f"Error reading CSV {csv_file_path}: {e}")
            return
    
    def write_csv_streaming(self, data_generator: Generator[Dict[str, Any], None, None],
                           csv_file_path: Path, headers: List[str], sanitizer=None) -> None:
        """
        Write CSV data using streaming for memory efficiency.
        
        Args:
            data_generator: Generator yielding row dictionaries
            csv_file_path: Path to output CSV file
            headers: List of column headers
            sanitizer: Optional sanitizer for data cleaning
        """
        try:
            with open(csv_file_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                
                for row in data_generator:
                    if sanitizer:
                        row = {k: sanitizer.sanitize_csv_field(v) for k, v in row.items()}
                    writer.writerow(row)
                    
        except Exception as e:
            print(f"Error writing CSV {csv_file_path}: {e}")
            raise


class ConsoleLogger:
    """
    Context manager for logging console output to a file.
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        Initialize the console logger.
        
        Args:
            log_file_path: Path to the log file, or None to skip logging
        """
        self.log_file_path = log_file_path
        self.log_file = None
        self.original_stdout = None
        self.original_stderr = None
    
    def __enter__(self):
        """Enter the context manager."""
        if self.log_file_path:
            try:
                self.log_file = open(self.log_file_path, 'w', encoding='utf-8')
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
                
                # Create a tee that writes to both stdout and file
                class Tee:
                    def __init__(self, *files):
                        self.files = files
                    
                    def write(self, data):
                        for f in self.files:
                            f.write(data)
                            f.flush()
                    
                    def flush(self):
                        for f in self.files:
                            f.flush()
                
                sys.stdout = Tee(self.original_stdout, self.log_file)
                sys.stderr = Tee(self.original_stderr, self.log_file)
                
                print(f"Console logging enabled: {self.log_file_path}")
            except Exception as e:
                print(f"Warning: Could not enable console logging: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self.log_file:
            # Restore original stdout/stderr
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr
            
            self.log_file.close()
            
            if not exc_type:
                print(f"Console log saved to: {self.log_file_path}")
        
        return False
