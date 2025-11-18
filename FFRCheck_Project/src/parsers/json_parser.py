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
                                start_addr_array = fuse.get('StartAddress', [])
                                end_addr_array = fuse.get('EndAddress', [])
                                
                                row_data = {
                                    'RegisterName': register_name,
                                    'FuseGroup_Name': group_name,
                                    'Fuse_Name': fuse_name,
                                    'StartAddress': self._format_start_address(start_addr_array),
                                    'EndAddress': self._format_end_address(end_addr_array)
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
    
    def _format_start_address(self, address_array: List[Any]) -> str:
        """
        Format start address array - returns the minimum address (start of range).
        
        Args:
            address_array: List of addresses
            
        Returns:
            String representation of the start address
        """
        if not address_array:
            return ''
        # If single address, return it
        if len(address_array) == 1:
            return str(int(address_array[0]))
        # If multiple addresses, return the minimum (start address)
        return str(int(min(address_array)))
    
    def _format_end_address(self, address_array: List[Any]) -> str:
        """
        Format end address array - returns the maximum address (end of range).
        
        Args:
            address_array: List of addresses
            
        Returns:
            String representation of the end address
        """
        if not address_array:
            return ''
        # If single address, return it
        if len(address_array) == 1:
            return str(int(address_array[0]))
        # If multiple addresses, return the maximum (end address)
        return str(int(max(address_array)))
    
    def _format_address_array(self, address_array: List[Any]) -> str:
        """
        Format an address array - returns the first address for single value or first address of range.
        DEPRECATED: Use _format_start_address or _format_end_address instead.
        
        Args:
            address_array: List of addresses
            
        Returns:
            String representation of the start address
        """
        if not address_array:
            return ''
        # If single address, return it
        if len(address_array) == 1:
            return str(int(address_array[0]))
        # If multiple addresses, return the minimum (start address)
        return str(int(min(address_array)))
