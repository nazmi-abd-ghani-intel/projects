"""JSON Parser for fuseDef.json files"""

import json
from typing import List, Dict, Any
from pathlib import Path


class JSONParser:
    """
    Parses fuseDef.json files and extracts fuse definitions.
    """
    
    def __init__(self, sanitizer):
        """
        Initialize the JSON parser.
        
        Args:
            sanitizer: CSVSanitizer instance for data cleaning
        """
        self.sanitizer = sanitizer
    
    def parse_json_optimized(self, json_file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse JSON file with optimization.
        
        Args:
            json_file_path: Path to the JSON file
            
        Returns:
            List of dictionaries containing parsed data
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"\nSuccessfully parsed: {json_file_path}")
            print("-" * 60)
            
            csv_data = []
            
            if 'Registers' not in data:
                print("❌ 'Registers' key not found in JSON")
                return []
            
            registers = data['Registers']
            print(f"Found {len(registers)} Register(s)")
            
            for register in registers:
                registers_data = register.get('RegistersData', [])
                
                for reg_data in registers_data:
                    register_name = reg_data.get('RegisterName', '')
                    
                    fuse_groups = register.get('FuseGroups', [])
                    
                    if fuse_groups:
                        for fuse_group in fuse_groups:
                            group_name = fuse_group.get('Name', '')
                            fuses = fuse_group.get('Fuses', [])
                            
                            for fuse in fuses:
                                fuse_name = fuse.get('Name', '')
                                
                                row_data = {
                                    'RegisterName': register_name,
                                    'FuseGroup_Name': group_name,
                                    'Fuse_Name': fuse_name,
                                    'StartAddress': self._format_address_array(fuse.get('StartAddress', [])),
                                    'EndAddress': self._format_address_array(fuse.get('EndAddress', []))
                                }
                                
                                csv_data.append(row_data)
                    else:
                        row_data = {
                            'RegisterName': register_name,
                            'FuseGroup_Name': '',
                            'Fuse_Name': '',
                            'StartAddress': '',
                            'EndAddress': ''
                        }
                        csv_data.append(row_data)
            
            print(f"\n✅ JSON parsing completed: {len(csv_data)} records extracted")
            return csv_data
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            return []
        except FileNotFoundError:
            print(f"Error: File '{json_file_path}' not found")
            return []
        except Exception as e:
            print(f"Unexpected error parsing JSON: {e}")
            return []
    
    def _format_address_array(self, address_array: List[Any]) -> str:
        """
        Format an address array as a comma-separated string.
        
        Args:
            address_array: List of addresses
            
        Returns:
            Comma-separated string of addresses
        """
        if not address_array:
            return ''
        return ','.join(str(self.sanitizer.sanitize_csv_field(addr)) for addr in address_array)
