"""Sspec Parser for sspec.txt files"""

from typing import List, Dict, Any, Set, Tuple
from pathlib import Path


class SspecParser:
    """
    Parses sspec.txt files and extracts fuse data for specific QDFs.
    """
    
    def __init__(self, file_processor):
        """
        Initialize the sspec parser.
        
        Args:
            file_processor: FileProcessor instance
        """
        self.file_processor = file_processor
    
    def parse_sspec_file_optimized(self, sspec_file_path: Path, target_qdf_set: Set[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse sspec.txt file with memory optimization.
        
        Args:
            sspec_file_path: Path to the sspec.txt file
            target_qdf_set: Set of target QDF identifiers
            
        Returns:
            Tuple of (list of parsed data, list of QDF identifiers)
        """
        try:
            target_qdf_list = list(target_qdf_set)
            
            print(f"Successfully opened: {sspec_file_path}")
            print(f"Target QDFs: {target_qdf_list}")
            print("-" * 60)
            
            sspec_data = []
            line_count = 0
            
            for line in self.file_processor.read_file_lines(sspec_file_path):
                line_count += 1
                if not line or not line.startswith('FUSEDATA:'):
                    continue
                
                if line_count % 10000 == 0:
                    print(f"  Processed {line_count} lines...")
                
                parts = line.split(':', 4)
                
                if len(parts) >= 5:
                    register_name = parts[1].strip()
                    qdf = parts[2].strip()
                    fuse_string = parts[4].strip()
                    
                    if qdf in target_qdf_set:
                        sspec_data.append({
                            'RegisterName': register_name,
                            'QDF': qdf,
                            'fuse_string': fuse_string,
                            'line_number': line_count
                        })
            
            print(f"\n✅ sspec.txt parsing completed: {len(sspec_data)} entries found for QDFs {target_qdf_list}")
            return sspec_data, target_qdf_list
            
        except Exception as e:
            print(f"❌ Error parsing sspec.txt: {e}")
            return [], []
