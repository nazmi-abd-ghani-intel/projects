"""CSV Processor for generating various CSV reports"""

from typing import List, Dict, Any
from pathlib import Path


class CSVProcessor:
    """
    Handles CSV generation and data processing operations.
    """
    
    def __init__(self, sanitizer, file_processor):
        """
        Initialize the CSV processor.
        
        Args:
            sanitizer: CSVSanitizer instance
            file_processor: FileProcessor instance
        """
        self.sanitizer = sanitizer
        self.file_processor = file_processor
    
    def write_csv_optimized(self, data: List[Dict[str, Any]], csv_file_path: Path, headers: List[str]) -> None:
        """
        Write CSV file with optimization.
        
        Args:
            data: List of dictionaries to write
            csv_file_path: Path to output CSV file
            headers: List of column headers
        """
        try:
            def data_generator():
                for row in data:
                    yield row
            
            self.file_processor.write_csv_streaming(data_generator(), csv_file_path, headers, self.sanitizer)
        except Exception as e:
            print(f"Error writing CSV file: {e}")
            raise
    
    def create_matched_csv(self, xml_data: List[Dict[str, Any]], json_data: List[Dict[str, Any]], 
                          output_csv_path: Path) -> List[Dict[str, Any]]:
        """
        Create a CSV matching XML and JSON data.
        
        Args:
            xml_data: Parsed XML data
            json_data: Parsed JSON data
            output_csv_path: Path to output CSV file
            
        Returns:
            List of combined data rows
        """
        from collections import defaultdict
        
        print(f"\n🔄 Creating matched CSV...")
        print(f"XML records: {len(xml_data)}")
        print(f"JSON records: {len(json_data)}")
        print("-" * 60)
        
        # Build index dictionaries for fast lookup (O(1) instead of O(n))
        print("📊 Building lookup indices for faster matching...")
        register_index = {}
        fusegroup_index = {}
        fusename_index = {}
        
        for json_row in json_data:
            register_name = json_row.get('RegisterName', '').strip()
            fusegroup_name = json_row.get('FuseGroup_Name', '').strip()
            fuse_name = json_row.get('Fuse_Name', '').strip()
            
            # Index by RegisterName (first match only)
            if register_name and register_name not in register_index:
                register_index[register_name] = json_row
            
            # Index by FuseGroup_Name
            if fusegroup_name:
                fusegroup_index[fusegroup_name] = json_row
            
            # Index by Fuse_Name
            if fuse_name:
                fusename_index[fuse_name] = json_row
        
        print(f"✅ Indices built: {len(register_index)} registers, {len(fusegroup_index)} fusegroups, {len(fusename_index)} fusenames")
        
        combined_data = []
        mismatch_details = {
            'register_mismatches': [],
            'fusegroup_mismatches': [],
            'fusename_mismatches': []
        }
        
        per_register_mismatches = defaultdict(lambda: {
            'register_mismatches': 0,
            'fusegroup_mismatches': 0,
            'fusename_mismatches': 0,
            'total_tokens': 0,
            'mismatch_tokens': []
        })
        
        # Progress indicator for large datasets
        total_rows = len(xml_data)
        progress_interval = max(1, total_rows // 10)  # Show progress every 10%
        
        for idx, xml_row in enumerate(xml_data):
            if (idx + 1) % progress_interval == 0:
                print(f"  Processing: {idx + 1}/{total_rows} ({100 * (idx + 1) // total_rows}%)")
            
            xml_fuse_register = xml_row.get('fuse_register', '').strip()
            xml_fuse_name = xml_row.get('fuse_name', '').strip()
            
            # Fast dictionary lookup instead of nested loop
            register_match = 'no-match'
            fusegroup_match = 'no-match'
            fusename_match = 'no-match'
            matched_json_row_for_register = None
            matched_json_row_for_fuse = None
            
            # Check register match (O(1) lookup)
            if xml_fuse_register and xml_fuse_register in register_index:
                register_match = 'match'
                matched_json_row_for_register = register_index[xml_fuse_register]
            
            # Check fusegroup match (O(1) lookup)
            if xml_fuse_name and xml_fuse_name in fusegroup_index:
                fusegroup_match = 'match'
                matched_json_row_for_fuse = fusegroup_index[xml_fuse_name]
            
            # Check fusename match (O(1) lookup)
            if xml_fuse_name and xml_fuse_name in fusename_index:
                fusename_match = 'match'
                matched_json_row_for_fuse = fusename_index[xml_fuse_name]
            
            mismatch_row_data = {
                'token_name_MTL': xml_row.get('token_name', ''),
                'field_name_MTL': xml_row.get('field_name', ''),
                'module_MTL': xml_row.get('module', ''),
                'fuse_register_MTL': xml_fuse_register,
                'fuse_name_MTL': xml_fuse_name,
                'first_socket_upload_MTL': xml_row.get('first_socket_upload', ''),
                'ssid_MTL': xml_row.get('ssid', ''),
                'ref_level_MTL': xml_row.get('ref_level', '')
            }
            
            register_key = xml_fuse_register if xml_fuse_register else 'N/A'
            per_register_mismatches[register_key]['total_tokens'] += 1
            
            if register_match == 'no-match' and xml_fuse_register:
                mismatch_details['register_mismatches'].append(mismatch_row_data)
                per_register_mismatches[register_key]['register_mismatches'] += 1
                per_register_mismatches[register_key]['mismatch_tokens'].append(mismatch_row_data)
            
            if fusegroup_match == 'no-match' and xml_fuse_name:
                mismatch_details['fusegroup_mismatches'].append(mismatch_row_data)
                per_register_mismatches[register_key]['fusegroup_mismatches'] += 1
                if mismatch_row_data not in per_register_mismatches[register_key]['mismatch_tokens']:
                    per_register_mismatches[register_key]['mismatch_tokens'].append(mismatch_row_data)
            
            if fusename_match == 'no-match' and xml_fuse_name:
                mismatch_details['fusename_mismatches'].append(mismatch_row_data)
                per_register_mismatches[register_key]['fusename_mismatches'] += 1
                if mismatch_row_data not in per_register_mismatches[register_key]['mismatch_tokens']:
                    per_register_mismatches[register_key]['mismatch_tokens'].append(mismatch_row_data)
            
            combined_row = {
                'dff_token_id_MTL': xml_row.get('dff_token_id', ''),
                'token_name_MTL': xml_row.get('token_name', ''),
                'first_socket_upload_MTL': xml_row.get('first_socket_upload', ''),
                'upload_process_step_MTL': xml_row.get('upload_process_step', ''),
                'ssid_MTL': xml_row.get('ssid', ''),
                'ref_level_MTL': xml_row.get('ref_level', ''),
                'module_MTL': xml_row.get('module', ''),
                'field_name_MTL': xml_row.get('field_name', ''),
                'field_name_seq_MTL': xml_row.get('field_name_seq', 0),
                'fuse_name_ori_MTL': xml_row.get('fuse_name_ori', ''),
                'fuse_name_MTL': xml_row.get('fuse_name', ''),
                'fuse_register_ori_MTL': xml_row.get('fuse_register_ori', ''),
                'fuse_register_MTL': xml_row.get('fuse_register', ''),
                
                'RegisterName_fuseDef': matched_json_row_for_register.get('RegisterName', '') if matched_json_row_for_register else '',
                'FuseGroup_Name_fuseDef': self._get_fuse_field_value(matched_json_row_for_fuse, 'FuseGroup_Name', fusegroup_match),
                'Fuse_Name_fuseDef': self._get_fuse_field_value(matched_json_row_for_fuse, 'Fuse_Name', fusename_match),
                'StartAddress_fuseDef': self._get_address_field_value(matched_json_row_for_register, matched_json_row_for_fuse, 'StartAddress'),
                'EndAddress_fuseDef': self._get_address_field_value(matched_json_row_for_register, matched_json_row_for_fuse, 'EndAddress'),
                
                'register_match': register_match,
                'fusegroup_match': fusegroup_match,
                'fusename_match': fusename_match
            }
            
            combined_data.append(combined_row)
        
        if combined_data:
            headers = [
                'dff_token_id_MTL', 'token_name_MTL', 'first_socket_upload_MTL', 'upload_process_step_MTL',
                'ssid_MTL', 'ref_level_MTL', 'module_MTL', 'field_name_MTL', 'field_name_seq_MTL',
                'fuse_name_ori_MTL', 'fuse_name_MTL', 'fuse_register_ori_MTL', 'fuse_register_MTL',
                'RegisterName_fuseDef', 'FuseGroup_Name_fuseDef', 'Fuse_Name_fuseDef', 'StartAddress_fuseDef', 'EndAddress_fuseDef',
                'register_match', 'fusegroup_match', 'fusename_match'
            ]
            
            def data_generator():
                for row in combined_data:
                    yield row
            
            self.file_processor.write_csv_streaming(data_generator(), output_csv_path, headers, self.sanitizer)
            print(f"\n✅ Combined CSV file created: {output_csv_path}")
            print(f"📊 Total combined rows: {len(combined_data)}")
            
            self._print_match_statistics(combined_data, mismatch_details, per_register_mismatches)
            
            return combined_data
        else:
            print("❌ No combined data to write")
            return []
    
    def _get_fuse_field_value(self, json_row, field_name: str, match_status: str) -> str:
        """Get fuse field value based on match status."""
        if match_status == 'no-match':
            return 'N/A'
        elif json_row is not None:
            return json_row.get(field_name, 'N/A')
        else:
            return 'N/A'
    
    def _get_address_field_value(self, register_json_row, fuse_json_row, field_name: str) -> str:
        """Get address field value from appropriate JSON row."""
        if fuse_json_row is not None:
            return fuse_json_row.get(field_name, '')
        elif register_json_row is not None:
            return register_json_row.get(field_name, '')
        else:
            return ''
    
    def _print_match_statistics(self, combined_data: List[Dict[str, Any]], 
                               mismatch_details: Dict, 
                               per_register_mismatches: Dict) -> None:
        """Print detailed match statistics."""
        register_matches = sum(1 for row in combined_data if row['register_match'] == 'match')
        fusegroup_matches = sum(1 for row in combined_data if row['fusegroup_match'] == 'match')
        fusename_matches = sum(1 for row in combined_data if row['fusename_match'] == 'match')
        fusegroup_na = sum(1 for row in combined_data if row['FuseGroup_Name_fuseDef'] == 'N/A')
        fusename_na = sum(1 for row in combined_data if row['Fuse_Name_fuseDef'] == 'N/A')
        total_rows = len(combined_data)
        
        print(f"\n📊 Match Statistics:")
        print(f"  Total rows: {total_rows}")
        print(f"  Register matches: {register_matches} ({register_matches/total_rows*100:.1f}%)")
        print(f"  FuseGroup matches: {fusegroup_matches} ({fusegroup_matches/total_rows*100:.1f}%)")
        print(f"  FuseName matches: {fusename_matches} ({fusename_matches/total_rows*100:.1f}%)")
        print(f"  FuseGroup N/A: {fusegroup_na} ({fusegroup_na/total_rows*100:.1f}%)")
        print(f"  FuseName N/A: {fusename_na} ({fusename_na/total_rows*100:.1f}%)")
        
        print(f"\n⚠️  Mismatch Summary:")
        print(f"  Register mismatches: {len(mismatch_details['register_mismatches'])}")
        print(f"  FuseGroup mismatches: {len(mismatch_details['fusegroup_mismatches'])}")
        print(f"  FuseName mismatches: {len(mismatch_details['fusename_mismatches'])}")
        
        print(f"\n📋 Per-Register Mismatch Summary:")
        for register, stats in sorted(per_register_mismatches.items()):
            if stats['total_tokens'] > 0:
                print(f"  {register}:")
                print(f"    Total tokens: {stats['total_tokens']}")
                print(f"    Register mismatches: {stats['register_mismatches']} ({stats['register_mismatches']/stats['total_tokens']*100:.1f}%)")
                print(f"    FuseGroup mismatches: {stats['fusegroup_mismatches']} ({stats['fusegroup_mismatches']/stats['total_tokens']*100:.1f}%)")
                print(f"    FuseName mismatches: {stats['fusename_mismatches']} ({stats['fusename_mismatches']/stats['total_tokens']*100:.1f}%)")

    def create_dff_mtl_olf_check_csv(self, xml_data, ube_data, output_file):
        """Create xfuse-dff-unitData-check CSV matching XML tokens with UBE visual IDs."""
        from collections import Counter
        
        # Create lookup tables
        ube_lookup, ube_wfr_lookup, visual_ids = self._create_lookup_tables(ube_data)
        
        # Initialize statistics
        per_register_stats = {}
        missing_tokens = Counter()
        invalid_tokens = Counter()
        
        # Generate combined rows
        combined_rows = []
        for xml_row in xml_data:
            token_name = xml_row['token_name']
            ref_level = xml_row['ref_level']
            register = xml_row['fuse_register']
            
            # Initialize register stats
            if register not in per_register_stats:
                per_register_stats[register] = {
                    'total_tokens': 0,
                    'missing_tokens': 0,
                    'invalid_tokens': 0
                }
            per_register_stats[register]['total_tokens'] += 1
            
            # Build output row with ALL 14 XML columns using _MTL suffix
            output_row = {
                'dff_token_id_MTL': xml_row.get('dff_token_id', ''),
                'token_name_MTL': token_name,
                'first_socket_upload_MTL': xml_row.get('first_socket_upload', ''),
                'upload_process_step_MTL': xml_row.get('upload_process_step', ''),
                'ssid_MTL': xml_row.get('ssid', ''),
                'ref_level_MTL': ref_level,
                'module_MTL': xml_row.get('module', ''),
                'field_name_MTL': xml_row.get('field_name', ''),
                'field_name_seq_MTL': str(xml_row.get('field_name_seq', '1')),
                'fuse_name_ori_MTL': xml_row.get('fuse_name_ori', ''),
                'fuse_name_MTL': xml_row.get('fuse_name', ''),
                'fuse_register_ori_MTL': xml_row.get('fuse_register_ori', ''),
                'fuse_register_MTL': register,
                'global_type_MTL': xml_row.get('global_type', '')
            }
            
            # Lookup UBE data
            lookup_key = f"{token_name}|{ref_level}"
            ube_values = ube_lookup.get(lookup_key, {})
            
            # Fallback to WFR MDPOSITION lookup if no match
            if not ube_values:
                # Try WFR with MDPOSITION matching the ref_level
                wfr_key = f"{token_name}|WFR|{ref_level}"
                ube_values = ube_wfr_lookup.get(wfr_key, {})
                
                # Also try if XML says WFR but has MDPOSITION
                if not ube_values and 'WFR' in ref_level.upper():
                    mdposition = xml_row.get('MDPOSITION', '')
                    if mdposition:
                        wfr_key = f"{token_name}|WFR|{mdposition}"
                        ube_values = ube_wfr_lookup.get(wfr_key, {})
            
            # Add visual ID columns
            for visual_id in sorted(visual_ids):
                if visual_id in ube_values:
                    full_token_value = ube_values[visual_id]
                    
                    # Extract specific field value by field_name_seq
                    field_name_seq = xml_row.get('field_name_seq', '1')
                    try:
                        field_idx = int(field_name_seq) - 1
                        token_parts = full_token_value.split('|')
                        
                        if 0 <= field_idx < len(token_parts):
                            field_value = token_parts[field_idx].strip()
                            
                            # Check for invalid value (-999)
                            if field_value == '-999':
                                output_row[visual_id] = field_value
                                invalid_tokens[f"{register}|{token_name}"] += 1
                                per_register_stats[register]['invalid_tokens'] += 1
                            else:
                                output_row[visual_id] = field_value
                        else:
                            output_row[visual_id] = 'N/A'
                            missing_tokens[f"{register}|{token_name}"] += 1
                            per_register_stats[register]['missing_tokens'] += 1
                    except (ValueError, IndexError):
                        output_row[visual_id] = 'N/A'
                        missing_tokens[f"{register}|{token_name}"] += 1
                        per_register_stats[register]['missing_tokens'] += 1
                else:
                    output_row[visual_id] = 'N/A'
                    missing_tokens[f"{register}|{token_name}"] += 1
                    per_register_stats[register]['missing_tokens'] += 1
            
            combined_rows.append(output_row)
        
        # Define column order - ALL 14 XML fields with _MTL suffix + visual IDs
        base_columns = [
            'dff_token_id_MTL', 'token_name_MTL', 'first_socket_upload_MTL', 
            'upload_process_step_MTL', 'ssid_MTL', 'ref_level_MTL', 
            'module_MTL', 'field_name_MTL', 'field_name_seq_MTL', 
            'fuse_name_ori_MTL', 'fuse_name_MTL', 'fuse_register_ori_MTL', 
            'fuse_register_MTL', 'global_type_MTL'
        ]
        all_columns = base_columns + sorted(visual_ids)
        
        # Write CSV
        row_count = self.file_processor.write_csv_streaming(
            (row for row in combined_rows),
            output_file,
            all_columns
        )
        
        # Print statistics
        self._print_dff_check_statistics(per_register_stats, missing_tokens, invalid_tokens, row_count)
        
        return output_file
    
    def _create_lookup_tables(self, ube_data):
        """Create lookup dictionaries from UBE data."""
        ube_lookup = {}  # key: token_name|ref_level, value: {visual_id: token_value}
        ube_wfr_lookup = {}  # key: token_name|WFR|MDPOSITION, value: {visual_id: token_value}
        visual_ids = set()
        
        for ube_row in ube_data:
            token_name = ube_row['token_name']
            token_value = ube_row['tokenValue']
            ref_level = ube_row['ref_level']
            visual_id = ube_row['visualID']
            mdposition = ube_row.get('MDPOSITION', '')
            
            visual_ids.add(visual_id)
            
            # Primary lookup by token_name|ref_level
            lookup_key = f"{token_name}|{ref_level}"
            if lookup_key not in ube_lookup:
                ube_lookup[lookup_key] = {}
            ube_lookup[lookup_key][visual_id] = token_value
            
            # WFR MDPOSITION lookup
            if 'WFR' in ref_level.upper() and mdposition:
                wfr_key = f"{token_name}|WFR|{mdposition}"
                if wfr_key not in ube_wfr_lookup:
                    ube_wfr_lookup[wfr_key] = {}
                ube_wfr_lookup[wfr_key][visual_id] = token_value
        
        return ube_lookup, ube_wfr_lookup, visual_ids
    
    def _print_dff_check_statistics(self, per_register_stats, missing_tokens, invalid_tokens, total_rows):
        """Print statistics for dff unitData check."""
        print(f"\n📊 xfuse-dff-unitData-check Statistics:")
        print(f"  Total rows: {total_rows}")
        
        total_missing = sum(stats['missing_tokens'] for stats in per_register_stats.values())
        total_invalid = sum(stats['invalid_tokens'] for stats in per_register_stats.values())
        
        print(f"  Total missing tokens: {total_missing}")
        print(f"  Total invalid tokens (-999): {total_invalid}")
        
        print(f"\n📋 Per-Register Summary:")
        for register, stats in sorted(per_register_stats.items()):
            if stats['total_tokens'] > 0:
                print(f"  {register}:")
                print(f"    Total tokens: {stats['total_tokens']}")
                print(f"    Missing tokens: {stats['missing_tokens']} ({stats['missing_tokens']/stats['total_tokens']*100:.1f}%)")
                print(f"    Invalid tokens: {stats['invalid_tokens']} ({stats['invalid_tokens']/stats['total_tokens']*100:.1f}%)")
