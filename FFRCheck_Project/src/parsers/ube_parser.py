"""UBE Parser for unit data files"""

import re
import html
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import Counter

# Compile regex patterns once for reuse
MDPOSITION_PATTERN = re.compile(r'MDPOSITION=([^,]+)')
TOKEN_PATTERN = re.compile(r'([^=]+)=(.+)')


class UBEParser:
    """
    Parses UBE (Unit Board) files and extracts unit data.
    """
    
    def __init__(self, sanitizer, file_processor):
        """
        Initialize the UBE parser.
        
        Args:
            sanitizer: CSVSanitizer instance
            file_processor: FileProcessor instance
        """
        self.sanitizer = sanitizer
        self.file_processor = file_processor
    
    def parse_ube_file_optimized(self, ube_file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse UBE file with memory optimization.
        
        Args:
            ube_file_path: Path to the UBE file
            
        Returns:
            List of dictionaries containing parsed data
        """
        try:
            print(f"Successfully opened: {ube_file_path}")
            print("-" * 60)
            
            ube_data = []
            current_visual_id = None
            current_ult = None
            current_mdposition = None
            line_count = 0
            
            for line in self.file_processor.read_file_lines(ube_file_path):
                line_count += 1
                if not line:
                    continue
                
                if line_count % 10000 == 0:
                    print(f"Processing line {line_count}...")
                
                if line.startswith('UNIT,'):
                    current_visual_id = line[5:].strip()
                    current_ult = None
                    current_mdposition = None
                    continue
                
                if line.endswith(':'):
                    current_ult = line[:-1].strip()
                    current_mdposition = None
                    continue
                
                mdposition_match = MDPOSITION_PATTERN.search(line)
                if mdposition_match:
                    current_mdposition = mdposition_match.group(1)
                
                if current_visual_id and ',' in line:
                    parts = line.split(',', 2)
                    if len(parts) >= 2:
                        ref_level = parts[0].strip()
                        first_socket_upload = parts[1].strip()
                        
                        needs_mdposition = (ref_level == 'WFR')
                        mdposition_to_use = current_mdposition if needs_mdposition else ''
                        
                        if len(parts) > 2:
                            token_parts = parts[2].split(',')
                            for token_part in token_parts:
                                token_part = token_part.strip()
                                
                                if not token_part or token_part.startswith('MDPOSITION='):
                                    continue
                                
                                token_match = TOKEN_PATTERN.match(token_part)
                                if token_match:
                                    token_name, token_value = token_match.groups()
                                    token_name = token_name.strip()
                                    token_value = token_value.strip()
                                    
                                    # Decode HTML entities (e.g., &#x27; -> ')
                                    token_value = html.unescape(token_value)
                                    
                                    ube_data.append({
                                        'visualID': current_visual_id,
                                        'ULT': current_ult or 'N/A',
                                        'ref_level': ref_level,
                                        'first_socket_upload': first_socket_upload,
                                        'token_name': token_name,
                                        'tokenValue': token_value,
                                        'MDPOSITION': mdposition_to_use
                                    })
            
            print(f"Total lines processed: {line_count}")
            print(f"\n✅ UBE parsing completed: {len(ube_data)} entries extracted")
            return ube_data
            
        except Exception as e:
            print(f"❌ Error parsing UBE file: {e}")
            return []
    
    def print_ube_statistics(self, ube_data: List[Dict[str, Any]]) -> None:
        """
        Print detailed UBE statistics.
        
        Args:
            ube_data: Parsed UBE data
        """
        if not ube_data:
            print("No UBE data to analyze")
            return
        
        total_entries = len(ube_data)
        
        visual_ids = Counter()
        ults = Counter()
        ref_levels = Counter()
        tokens = Counter()
        mdpositions = Counter()
        
        for entry in ube_data:
            visual_id = entry.get('visualID', '')
            ult = entry.get('ULT', '')
            ref_level = entry.get('ref_level', '')
            token_name = entry.get('token_name', '')
            mdposition = entry.get('MDPOSITION', '').strip()
            
            visual_ids[visual_id] += 1
            if ult != 'N/A':
                ults[ult] += 1
            ref_levels[ref_level] += 1
            tokens[token_name] += 1
            
            if mdposition:
                mdpositions[mdposition] += 1
            else:
                mdpositions['No MDPOSITION'] += 1
        
        print(f"\n📊 UBE Parsing Statistics:")
        print(f"  Total entries: {total_entries}")
        print(f"  Unique Visual IDs: {len(visual_ids)}")
        print(f"  Unique ULTs: {len(ults)}")
        print(f"  Unique ref_levels: {len(ref_levels)}")
        print(f"  Unique token names: {len(tokens)}")
        print(f"  Unique MDPOSITION values: {len(mdpositions) - (1 if 'No MDPOSITION' in mdpositions else 0)}")
        
        print(f"\n  📋 Breakdown by ref_level:")
        for ref_level, count in ref_levels.most_common():
            print(f"    {ref_level}: {count} entries ({count/total_entries*100:.1f}%)")
        
        print(f"\n  📋 Breakdown by MDPOSITION:")
        for mdposition, count in mdpositions.most_common():
            print(f"    {mdposition}: {count} entries ({count/total_entries*100:.1f}%)")
    
    def extract_lotname_location_from_ube(self, ube_file_path: Path) -> Tuple[str, str]:
        """
        Extract lot name and location from UBE file path.
        
        Args:
            ube_file_path: Path to the UBE file
            
        Returns:
            Tuple of (lotname, location)
        """
        filename = ube_file_path.stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            lotname = '_'.join(parts[:-1])
            location = parts[-1]
        else:
            lotname = filename
            location = 'unknown'
        
        print(f"📝 Extracted from UBE filename: lotname='{lotname}', location='{location}'")
        return lotname, location
