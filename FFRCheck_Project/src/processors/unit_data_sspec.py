"""Unit Data SSPEC Processor - Maps ITF unit data to SSPEC breakdown"""

import csv
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict


class UnitDataSspecProcessor:
    """Process unit data from ITF and map to SSPEC breakdown."""
    
    def __init__(self):
        """Initialize the processor."""
        pass
    
    def decode_rle(self, rle_string: str) -> str:
        """
        Decode RLE (Running Length Encoder) format to binary string.
        
        Format: A5BA2B3 = 00000100111
        - A followed by number means that many '0's (A without number = 1 zero)
        - B followed by number means that many '1's (B without number = 1 one)
        
        Args:
            rle_string: RLE encoded string
            
        Returns:
            Binary string
        """
        if not rle_string:
            return ''
        
        binary = []
        i = 0
        
        while i < len(rle_string):
            char = rle_string[i]
            
            if char.upper() == 'A':
                # A means zeros
                i += 1
                # Collect all digits following A
                num_str = ''
                while i < len(rle_string) and rle_string[i].isdigit():
                    num_str += rle_string[i]
                    i += 1
                
                # If no number, default to 1
                count = int(num_str) if num_str else 1
                binary.append('0' * count)
            
            elif char.upper() == 'B':
                # B means ones
                i += 1
                # Collect all digits following B
                num_str = ''
                while i < len(rle_string) and rle_string[i].isdigit():
                    num_str += rle_string[i]
                    i += 1
                
                # If no number, default to 1
                count = int(num_str) if num_str else 1
                binary.append('1' * count)
            else:
                i += 1
        
        return ''.join(binary)
    
    def is_binary_string(self, value: str) -> bool:
        """Check if string is already in binary format."""
        if not value:
            return False
        # Check if string contains only 0s and 1s
        return all(c in '01' for c in value.strip())
    
    def normalize_tname_value(self, tname_value: str) -> str:
        """
        Normalize TNAME_VALUE to binary format.
        
        Args:
            tname_value: Either binary string or RLE encoded string
            
        Returns:
            Binary string
        """
        if not tname_value:
            return ''
        
        # Check if already binary
        if self.is_binary_string(tname_value):
            return tname_value.strip()
        
        # Otherwise decode as RLE
        return self.decode_rle(tname_value)
    
    def extract_fuse_bits(self, full_binary: str, start_addr: int, end_addr: int) -> str:
        """
        Extract bits from full binary string based on start and end addresses.
        
        Args:
            full_binary: Complete binary string for register
            start_addr: Start bit address
            end_addr: End bit address
            
        Returns:
            Extracted binary substring
        """
        if not full_binary:
            return ''
        
        fuse_length = len(full_binary)
        
        # Handle bit ordering (LSB)
        if start_addr > end_addr:
            start_addr, end_addr = end_addr, start_addr
        
        lsb_start = max(0, fuse_length - 1 - end_addr)
        lsb_end = min(fuse_length - 1, fuse_length - 1 - start_addr)
        
        if lsb_start <= lsb_end:
            return full_binary[lsb_start:lsb_end + 1]
        
        return ''
    
    def binary_to_hex(self, binary_str: str) -> str:
        """Convert binary string to hex."""
        if not binary_str:
            return ''
        
        try:
            return '0X' + hex(int(binary_str, 2))[2:].upper()
        except ValueError:
            return ''
    
    def load_itf_fullstring_data(self, itf_file: Path) -> Dict[str, Dict[str, str]]:
        """
        Load ITF fullstring data and organize by visualID and register.
        
        Args:
            itf_file: Path to ITF fullstring CSV file
            
        Returns:
            Dict[visualID][register] = binary_data
        """
        unit_data = defaultdict(dict)
        
        with open(itf_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                visual_id = row.get('visualid', '')
                register = row.get('Register', '')
                tname_value = row.get('TNAME_VALUE', '')
                
                if visual_id and register and tname_value:
                    # Normalize to binary
                    binary_data = self.normalize_tname_value(tname_value)
                    unit_data[visual_id][register] = binary_data
        
        return dict(unit_data)
    
    def create_unit_data_sspec_csv(self, sspec_file: Path, itf_file: Path, 
                                   output_file: Path, qdf: str, dff_file: Path = None, 
                                   input_dir: Path = None) -> bool:
        """
        Create S_UnitData_by_Fuse CSV file with ITF and DFF data.
        
        Args:
            sspec_file: Path to existing S_SSPEC_Breakdown CSV
            itf_file: Path to ITF fullstring CSV
            output_file: Path for output CSV
            qdf: QDF name
            dff_file: Path to V_Report_DFF_UnitData CSV (optional)
            input_dir: Input directory containing FleFuseSettings.json (optional)
            
        Returns:
            True if successful
        """
        print(f"\n🔄 Creating S_UnitData_by_Fuse for QDF '{qdf}'...")
        
        # Load ITF unit data
        unit_data = self.load_itf_fullstring_data(itf_file)
        
        if not unit_data:
            print(f"⚠️  No unit data found in {itf_file.name}")
            return False
        
        visual_ids = sorted(unit_data.keys())
        print(f"  Found {len(visual_ids)} units: {', '.join(visual_ids)}")
        
        # Load DFF data if available
        dff_data = {}
        if dff_file and dff_file.exists():
            dff_data = self.load_dff_data(dff_file, visual_ids)
            if dff_data:
                print(f"  Loaded DFF data for comparison")
        
        # Load FLE fuses if available
        fle_fuses = set()
        if input_dir:
            fle_fuses = self.load_fle_fuses(input_dir)
            if fle_fuses:
                print(f"  Loaded {len(fle_fuses)} FLE fuses from FleFuseSettings.json")
        
        # Read sspec data
        with open(sspec_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sspec_rows = list(reader)
            fieldnames = reader.fieldnames
        
        # Create new fieldnames with visual IDs and DFF columns
        new_fieldnames = list(fieldnames)
        for vid in visual_ids:
            new_fieldnames.append(f'{vid}_ITF_binaryValue')
            new_fieldnames.append(f'{vid}_ITF_hexValue')
            if dff_data:
                new_fieldnames.append(f'{vid}_DFF_value')
            new_fieldnames.append(f'{vid}_StatusCheck')
        
        # Process each row and add unit data
        processed_rows = []
        
        for row in sspec_rows:
            new_row = dict(row)
            register_name = row.get('RegisterName', '')
            fuse_name = row.get('Fuse_Name_fuseDef', '')
            fuse_group = row.get('FuseGroup_Name_fuseDef', '')
            start_addr_str = row.get('StartAddress_fuseDef', '')
            end_addr_str = row.get('EndAddress_fuseDef', '')
            
            # Get QDF hex value for static comparison
            qdf_hex_value = row.get(f'{qdf}_hexValue', '')
            
            # Check if QDF binary value contains 's' (sort-skip)
            qdf_binary = row.get(f'{qdf}_binaryValue', '')
            has_sort_skip = 's' in qdf_binary.lower() if qdf_binary else False
            
            # Parse addresses
            try:
                start_addr = int(start_addr_str) if start_addr_str else 0
                end_addr = int(end_addr_str) if end_addr_str else 0
            except ValueError:
                start_addr = 0
                end_addr = 0
            
            # Add data for each visual ID
            for vid in visual_ids:
                binary_value = ''
                hex_value = ''
                
                # Get ITF data
                if register_name in unit_data[vid]:
                    full_binary = unit_data[vid][register_name]
                    binary_value = self.extract_fuse_bits(full_binary, start_addr, end_addr)
                    hex_value = self.binary_to_hex(binary_value)
                
                new_row[f'{vid}_ITF_binaryValue'] = f'b{binary_value}' if binary_value else 'N/A'
                new_row[f'{vid}_ITF_hexValue'] = hex_value if hex_value else 'N/A'
                
                # Add DFF data if available
                if dff_data:
                    # Check if QDF binary has sort-skip marker
                    if has_sort_skip:
                        dff_value = 'sort-skip'
                    else:
                        # Try FuseGroup first (MTL_OLF maps to FuseGroups), then individual fuse name
                        dff_key_group = f"{fuse_group}|{register_name}"
                        dff_key_fuse = f"{fuse_name}|{register_name}"
                        dff_value = dff_data.get(vid, {}).get(dff_key_group, 
                                   dff_data.get(vid, {}).get(dff_key_fuse, 'N/A'))
                        
                        # If DFF is N/A, check if it's an FLE fuse
                        if dff_value == 'N/A':
                            # Check FuseGroup first (primary), then individual fuse name
                            # Also check normalized versions (lowercase, / to _)
                            is_fle = (
                                fuse_group in fle_fuses or
                                fuse_group.lower() in fle_fuses or
                                fuse_group.replace('/', '_').lower() in fle_fuses or
                                fuse_name in fle_fuses or
                                fuse_name.lower() in fle_fuses or
                                fuse_name.replace('/', '_').lower() in fle_fuses
                            )
                            if is_fle:
                                dff_value = 'FLE'
                    
                    new_row[f'{vid}_DFF_value'] = dff_value
                
                # StatusCheck logic
                status_check = '!mismatch!'
                
                if dff_data:
                    dff_val = new_row.get(f'{vid}_DFF_value', 'N/A')
                    
                    # Priority order for status check
                    if dff_val == 'sort-skip':
                        status_check = 'sort'
                    elif dff_val == 'FLE':
                        status_check = 'FLE'
                    elif dff_val != 'N/A' and hex_value and hex_value != 'N/A':
                        # Check if DFF value matches ITF hex
                        # DFF can be binary, decimal, or hex (with or without 0X prefix)
                        # Strategy: Try all possible interpretations and use the one that matches ITF
                        dff_as_hex = 'N/A'
                        if dff_val:
                            try:
                                # Check if already hex format (with 0X prefix)
                                if dff_val.upper().startswith('0X'):
                                    dff_as_hex = dff_val.upper()
                                else:
                                    # Try all possible formats and check which matches ITF
                                    candidates = []
                                    
                                    # Try binary (only if all chars are 0 or 1)
                                    if all(c in '01' for c in dff_val):
                                        try:
                                            candidates.append(hex(int(dff_val, 2)).upper())
                                        except ValueError:
                                            pass
                                    
                                    # Try hex (if contains A-F or valid hex digits)
                                    try:
                                        candidates.append(hex(int(dff_val, 16)).upper())
                                    except ValueError:
                                        pass
                                    
                                    # Try decimal (only if all digits, for values like "38", "13")
                                    if dff_val.isdigit():
                                        try:
                                            candidates.append(hex(int(dff_val, 10)).upper())
                                        except ValueError:
                                            pass
                                    
                                    # Check which candidate matches ITF
                                    for candidate in candidates:
                                        if candidate == hex_value.upper():
                                            dff_as_hex = candidate
                                            break
                                    
                                    # If no match, use first candidate as default
                                    if dff_as_hex == 'N/A' and candidates:
                                        dff_as_hex = candidates[0]
                            except (ValueError, AttributeError):
                                pass
                        
                        if dff_as_hex == hex_value.upper():
                            status_check = 'dynamic'
                        elif qdf_hex_value and qdf_hex_value != 'N/A':
                            # DFF didn't match, check if QDF matches
                            if qdf_hex_value.upper() == hex_value.upper():
                                status_check = 'static'
                            else:
                                status_check = '!mismatch!'
                        else:
                            status_check = '!mismatch!'
                    elif qdf_hex_value and hex_value and qdf_hex_value != 'N/A' and hex_value != 'N/A':
                        # Check if QDF hex matches ITF hex
                        if qdf_hex_value.upper() == hex_value.upper():
                            status_check = 'static'
                        else:
                            status_check = '!mismatch!'
                else:
                    # No DFF data, only check QDF vs ITF
                    if qdf_hex_value and hex_value and qdf_hex_value != 'N/A' and hex_value != 'N/A':
                        if qdf_hex_value.upper() == hex_value.upper():
                            status_check = 'static'
                        else:
                            status_check = '!mismatch!'
                
                new_row[f'{vid}_StatusCheck'] = status_check
            
            processed_rows.append(new_row)
        
        # Write output CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(processed_rows)
        
        print(f"✅ Created: {output_file.name} ({len(processed_rows)} rows)")
        print(f"   Added columns for {len(visual_ids)} units")
        if dff_data:
            print(f"   Includes DFF comparison data")
        
        return True
    
    def load_dff_data(self, dff_file: Path, visual_ids: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Load DFF unit data from V_Report_DFF_UnitData CSV.
        
        Args:
            dff_file: Path to V_Report_DFF_UnitData CSV
            visual_ids: List of visual IDs to load
            
        Returns:
            Dict mapping visual_id -> {fuse_name|register: value}
        """
        dff_data = {vid: {} for vid in visual_ids}
        
        try:
            with open(dff_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    fuse_name = row.get('fuse_name_MTL', '')
                    register = row.get('fuse_register_MTL', '')
                    
                    if fuse_name and register:
                        key = f"{fuse_name}|{register}"
                        
                        for vid in visual_ids:
                            if vid in row:
                                dff_data[vid][key] = row[vid]
            
            return dff_data
        except Exception as e:
            print(f"⚠️  Error loading DFF data: {e}")
            return {}
    
    def load_fle_fuses(self, input_dir: Path) -> Set[str]:
        """
        Load FLE (Field Level Encryption) fuses from FleFuseSettings.json.
        
        Args:
            input_dir: Directory containing FleFuseSettings.json
            
        Returns:
            Set of FLE fuse/group names (normalized)
        """
        fle_file = input_dir / 'FleFuseSettings.json'
        if not fle_file.exists():
            return set()
        
        try:
            with open(fle_file, 'r', encoding='utf-8') as f:
                fle_data = json.load(f)
            
            fle_fuses = set()
            
            # Parse FleFuseSettings.json structure:
            # {"Registers": [{"Name": "...", "SecurityKeys": [{"SecurityKeyDecoder": [{"fuseName": "..."}]}], "SpecialFuses": {...}}]}
            if isinstance(fle_data, dict) and 'Registers' in fle_data:
                registers = fle_data['Registers']
                if isinstance(registers, list):
                    for register in registers:
                        if isinstance(register, dict):
                            # Process SecurityKeys -> SecurityKeyDecoder -> fuseName
                            if 'SecurityKeys' in register:
                                security_keys = register['SecurityKeys']
                                if isinstance(security_keys, list):
                                    for key in security_keys:
                                        if isinstance(key, dict) and 'SecurityKeyDecoder' in key:
                                            decoders = key['SecurityKeyDecoder']
                                            if isinstance(decoders, list):
                                                for decoder in decoders:
                                                    if isinstance(decoder, dict) and 'fuseName' in decoder:
                                                        fuse_name = decoder['fuseName']
                                                        if fuse_name:  # Not empty
                                                            # Add original name
                                                            fle_fuses.add(fuse_name)
                                                            # Add normalized version (replace / with _, uppercase to lowercase)
                                                            normalized = fuse_name.replace('/', '_').lower()
                                                            fle_fuses.add(normalized)
                                                            # Add version with underscores in common patterns
                                                            if 'dfxagg' in normalized:
                                                                fle_fuses.add(normalized.replace('dfxagg', 'dfx_agg'))
                                                            if 'endebug' in normalized:
                                                                fle_fuses.add(normalized.replace('endebug', 'endebug'))
                                                                # Also try uppercase version
                                                                fle_fuses.add(fuse_name.replace('ENDEBUG', 'endebug'))
                            
                            # Process SpecialFuses -> LockoutBits -> fuseNames (FuseGroups)
                            if 'SpecialFuses' in register:
                                special_fuses = register['SpecialFuses']
                                if isinstance(special_fuses, dict):
                                    # LockoutBits -> fuseNames
                                    if 'LockoutBits' in special_fuses:
                                        lockout_bits = special_fuses['LockoutBits']
                                        if isinstance(lockout_bits, list):
                                            for lockout in lockout_bits:
                                                if isinstance(lockout, dict) and 'fuseNames' in lockout:
                                                    fuse_names = lockout['fuseNames']
                                                    if isinstance(fuse_names, list):
                                                        for fuse_group in fuse_names:
                                                            if fuse_group:  # Not empty
                                                                # Add FuseGroup name
                                                                fle_fuses.add(fuse_group)
                                                                # Add normalized version
                                                                normalized = fuse_group.replace('/', '_').lower()
                                                                fle_fuses.add(normalized)
                                    
                                    # SpecialAlgorithms -> Fuse (FuseGroup for hash/CRC algorithms)
                                    if 'SpecialAlgorithms' in special_fuses:
                                        special_algs = special_fuses['SpecialAlgorithms']
                                        if isinstance(special_algs, list):
                                            for alg in special_algs:
                                                if isinstance(alg, dict) and 'Fuse' in alg:
                                                    fuse_group = alg['Fuse']
                                                    if fuse_group:  # Not empty
                                                        # Add FuseGroup name
                                                        fle_fuses.add(fuse_group)
                                                        # Add normalized version
                                                        normalized = fuse_group.replace('/', '_').lower()
                                                        fle_fuses.add(normalized)
                                                
                                                # Also add IncludeFuses (individual fuses used in algorithm)
                                                if isinstance(alg, dict) and 'IncludeFuses' in alg:
                                                    include_fuses = alg['IncludeFuses']
                                                    if isinstance(include_fuses, list):
                                                        for inc_fuse in include_fuses:
                                                            if inc_fuse:  # Not empty
                                                                # Add fuse name
                                                                fle_fuses.add(inc_fuse)
                                                                # Add normalized version
                                                                normalized = inc_fuse.replace('/', '_').lower()
                                                                fle_fuses.add(normalized)
            
            return fle_fuses
            
        except Exception as e:
            print(f"⚠️  Error loading FLE fuses from {fle_file}: {e}")
            return set()
