"""Sspec Parser for sspec.txt files"""

import csv
from typing import List, Dict, Any, Set, Tuple
from pathlib import Path
from collections import defaultdict
from ..utils.helpers import analyze_fuse_string_bits, binary_to_hex_fast, breakdown_fuse_string_fast


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
    
    def create_sspec_breakdown_csv(self, sspec_data: List[Dict[str, Any]], fusedef_csv_path: Path,
                                  output_dir: Path, fusefilename: str, target_qdf_list: List[str]) -> bool:
        """Create xsplit-sspec breakdown CSVs."""
        print(f"\n🔄 Creating xsplit-sspec breakdown CSVs...")
        print(f"  sspec entries: {len(sspec_data)}")
        print(f"  FUSEDEF CSV: {fusedef_csv_path.name}")
        print(f"  Target QDFs: {target_qdf_list}")
        print("-" * 60)
        
        try:
            fusedef_data = list(self.file_processor.process_large_csv_generator(str(fusedef_csv_path)))
            print(f"✅ Loaded {len(fusedef_data)} entries from FUSEDEF CSV")
        except Exception as e:
            print(f"❌ Error reading FUSEDEF CSV: {e}")
            return False
        
        if not fusedef_data:
            print("❌ No fuseDef data loaded")
            return False
        
        # Group sspec by register and QDF
        sspec_by_register = defaultdict(dict)
        for sspec_entry in sspec_data:
            register_name = sspec_entry['RegisterName']
            qdf = sspec_entry['QDF']
            sspec_by_register[register_name][qdf] = sspec_entry
        
        print(f"\n📊 Processing {len(sspec_by_register)} unique registers")
        
        # Process each QDF separately to create individual CSVs
        for qdf in target_qdf_list:
            print(f"\n  Creating CSV for QDF: {qdf}")
            breakdown_data = []
            
            for register_name, qdf_data in sspec_by_register.items():
                if qdf not in qdf_data:
                    continue
                
                sspec_entry = qdf_data[qdf]
                fuse_string = sspec_entry['fuse_string']
                
                # Find matching fusedef entries
                matching_fusedef = [row for row in fusedef_data 
                                  if row.get('RegisterName_fuseDef', '') == register_name]
                
                if not matching_fusedef:
                    # Add N/A entry
                    breakdown_data.append({
                        'RegisterName': register_name,
                        'RegisterName_fuseDef': 'N/A',
                        'FuseGroup_Name_fuseDef': 'N/A',
                        'Fuse_Name_fuseDef': 'N/A',
                        'StartAddress_fuseDef': 'N/A',
                        'EndAddress_fuseDef': 'N/A',
                        'bit_length': 0,
                        f'{qdf}_binaryValue': 'N/A',
                        f'{qdf}_hexValue': 'Q'
                    })
                    continue
                
                # Process each fusedef row
                for fusedef_row in matching_fusedef:
                    start_addr = fusedef_row.get('StartAddress_fuseDef', '')
                    end_addr = fusedef_row.get('EndAddress_fuseDef', '')
                    
                    extracted_bits = ''
                    bit_length = 0
                    hex_value = 'Q'
                    binary_value_with_prefix = 'N/A'
                    
                    if start_addr and end_addr and start_addr != '' and end_addr != '':
                        extracted_bits = breakdown_fuse_string_fast(fuse_string, start_addr, end_addr)
                        bit_length = len(extracted_bits) if extracted_bits else 0
                        
                        hex_value = binary_to_hex_fast(extracted_bits)
                        
                        if extracted_bits:
                            binary_value_with_prefix = f"b{extracted_bits}"
                        else:
                            binary_value_with_prefix = 'N/A'
                    
                    breakdown_data.append({
                        'RegisterName': register_name,
                        'RegisterName_fuseDef': fusedef_row.get('RegisterName_fuseDef', ''),
                        'FuseGroup_Name_fuseDef': fusedef_row.get('FuseGroup_Name_fuseDef', ''),
                        'Fuse_Name_fuseDef': fusedef_row.get('Fuse_Name_fuseDef', ''),
                        'StartAddress_fuseDef': fusedef_row.get('StartAddress_fuseDef', ''),
                        'EndAddress_fuseDef': fusedef_row.get('EndAddress_fuseDef', ''),
                        'bit_length': bit_length,
                        f'{qdf}_binaryValue': binary_value_with_prefix,
                        f'{qdf}_hexValue': hex_value
                    })
            
            if breakdown_data:
                # Write CSV for this QDF
                output_csv = output_dir / f"xsplit-sspec_{qdf}_{fusefilename}.csv"
                headers = [
                    'RegisterName', 'RegisterName_fuseDef', 'FuseGroup_Name_fuseDef', 'Fuse_Name_fuseDef',
                    'StartAddress_fuseDef', 'EndAddress_fuseDef', 'bit_length',
                    f'{qdf}_binaryValue', f'{qdf}_hexValue'
                ]
                
                with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(breakdown_data)
                
                print(f"  ✅ Created: {output_csv.name} ({len(breakdown_data)} rows)")
        
        print(f"\n✅ All xsplit-sspec CSVs created successfully")
        return True
