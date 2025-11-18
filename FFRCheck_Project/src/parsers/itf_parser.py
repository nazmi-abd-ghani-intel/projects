"""
ITF Parser Module
Handles parsing of ITF files with full functionality
"""

import gzip
import re
import tempfile
import shutil
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime

# SSID mapping table for TNAME pattern matching
SSID_MAPPING_TABLE = [
    ('IPC::FUS', 'CPU0', 'U1.U5', ['FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU0']),
    ('IPC::FUS', 'CPU1', 'U1.U6', ['FACTFUSBURNCPUNOM_X_X_X_X_LOCKBIT_RAP_CPU1']),
    ('IPG::FUS', 'GCD', 'U1.U4', ['FACTFUSBURNGCDNOM_X_X_X_X_LOCKBIT_RAP_GCD']),
    ('IPH::FUS', 'HUB', 'U1.U2', ['FACTFUSBURNHUBNOM_X_X_X_X_LOCKBIT_RAP_HUB']),
    ('IPP::FUS', 'PCD', 'U1.U3', ['FACTFUSBURNPCDNOM_X_X_X_X_LOCKBITRAP_PCD']),
]


class ITFParser:
    """Parser for ITF files."""
    
    def __init__(self):
        pass
    
    def extract_gz_file(self, gz_file_path: Path) -> Optional[Path]:
        """Extract .gz file to temporary directory."""
        try:
            temp_dir = Path(tempfile.mkdtemp())
            base_name = gz_file_path.name
            extracted_name = base_name[:-3] if base_name.endswith('.gz') else base_name + '_extracted'
            extracted_path = temp_dir / extracted_name
            
            with gzip.open(gz_file_path, 'rb') as gz_file:
                with open(extracted_path, 'wb') as extracted_file:
                    shutil.copyfileobj(gz_file, extracted_file)
            
            print(f"  Extracted {gz_file_path.name} to temp location")
            return extracted_path
        except Exception as e:
            print(f"❌ Error extracting {gz_file_path}: {e}")
            return None
    
    def find_itf_files(self, directory_path: Path) -> List[Path]:
        """Find all .itf and .itf.gz files in directory."""
        itf_files = []
        if not directory_path.exists() or not directory_path.is_dir():
            print(f"❌ Error: Directory {directory_path} does not exist")
            return itf_files
        
        try:
            for file_path in directory_path.iterdir():
                if file_path.is_dir():
                    continue
                
                if file_path.suffix == '.itf':
                    print(f"  Found ITF file: {file_path.name}")
                    itf_files.append(file_path)
                elif file_path.name.endswith('.itf.gz'):
                    print(f"  Found ITF.GZ file: {file_path.name}")
                    extracted_path = self.extract_gz_file(file_path)
                    if extracted_path and extracted_path.suffix == '.itf':
                        itf_files.append(extracted_path)
        except Exception as e:
            print(f"❌ Error reading directory {directory_path}: {e}")
        
        return itf_files
    
    def match_tname_patterns(self, tname: str, patterns: List[str]) -> bool:
        """Check if TNAME matches any pattern."""
        if not tname or not patterns:
            return False
        
        for pattern in patterns:
            try:
                if pattern in tname or re.search(pattern, tname, re.IGNORECASE):
                    return True
            except re.error:
                if pattern in tname:
                    return True
        return False
    
    def find_ssid_for_tname(self, tname: str) -> Optional[Tuple[str, str, str]]:
        """Find Domain, Register, SSID for given TNAME."""
        for domain, register, ssid, tname_patterns in SSID_MAPPING_TABLE:
            if self.match_tname_patterns(tname, tname_patterns):
                return domain, register, ssid
        return None
    
    def extract_base_tname(self, tname: str) -> str:
        """Extract base TNAME without _fdN suffix."""
        return re.sub(r'_fd\d+$', '', tname)
    
    def extract_fd_number(self, tname: str) -> int:
        """Extract FD number from TNAME."""
        match = re.search(r'_fd(\d+)$', tname)
        return int(match.group(1)) if match else 0
    
    def extract_ssid_and_value_from_line(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract SSID and value from ITF line."""
        if '_' in line:
            parts = line.split('_')
            if len(parts) >= 3:
                for i, part in enumerate(parts):
                    if re.match(r'U1\.U\d+', part) and i + 1 < len(parts):
                        return part, '_'.join(parts[i+1:])
        return None, None
    
    def parse_ult_data_for_unit(self, ult_lines_by_ssid: Dict[str, List[str]]) -> Dict[str, str]:
        """Parse ULT data for a unit."""
        ult_results = {}
        
        for ssid, lines in ult_lines_by_ssid.items():
            ult_data = {'lot': None, 'wafer': None, 'xloc': None, 'yloc': None}
            
            for line in lines:
                ssid_from_line, value = self.extract_ssid_and_value_from_line(line)
                if value:
                    if 'sstrlot_' in line:
                        ult_data['lot'] = value
                    elif 'sstrwafer_' in line:
                        ult_data['wafer'] = value
                    elif 'sstrxloc_' in line:
                        ult_data['xloc'] = value
                    elif 'sstryloc_' in line:
                        ult_data['yloc'] = value
            
            if all(ult_data.values()):
                ult_results[ssid] = f"{ult_data['lot']}_{ult_data['wafer']}_{ult_data['xloc']}_{ult_data['yloc']}"
            elif any(ult_data.values()):
                parts = [ult_data['lot'] or '', ult_data['wafer'] or '',
                        ult_data['xloc'] or '', ult_data['yloc'] or '']
                ult_results[ssid] = '_'.join(parts)
        
        return ult_results
    
    def extract_itf_data(self, itf_file_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """Extract header and unit data from ITF file."""
        header_data = {
            'lotid': None, 'sspec': None, 'prgnm': None, 'lcode': None,
            'sysid': None, 'facid': None, 'tempr': None
        }
        
        units = []
        current_unit = None
        current_unit_ult_lines = {}
        current_unit_tnames = {}
        pending_tname = None
        
        try:
            with open(itf_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Extract header fields
                    for prefix, key in [('6_lotid_', 'lotid'), ('6_sspec_', 'sspec'), ('6_prgnm_', 'prgnm'),
                                       ('5_lcode_', 'lcode'), ('4_sysid_', 'sysid'), ('4_facid_', 'facid'), ('4_tempr_', 'tempr')]:
                        if line.startswith(prefix):
                            header_data[key] = line[len(prefix):]
                    
                    # Unit processing
                    if line.startswith('3_lsep') or line.startswith('3_lbeg'):
                        if current_unit is not None:
                            current_unit['ult_data'] = self.parse_ult_data_for_unit(current_unit_ult_lines)
                            current_unit['tname_values'] = current_unit_tnames.copy()
                            units.append(current_unit)
                        
                        current_unit = {
                            'prtnm': None, 'thermalhdid': None, 'dvtststdt': None, 'socket': None,
                            'tstordnum': None, 'tiuid': None, 'eqpprtid': None, 'siteid': None,
                            'prttesterid': None, 'tiuprscdid': None, 'visualid': None, 'subflstpid': None,
                            'binn': None, 'curfbin': None, 'curibin': None, 'ult_data': {}, 'tname_values': {}
                        }
                        current_unit_ult_lines = {}
                        current_unit_tnames = {}
                        pending_tname = None
                    
                    elif line.startswith('3_') and current_unit is not None:
                        key_value = line[2:].split('_', 1)
                        if len(key_value) == 2 and key_value[0] in current_unit:
                            current_unit[key_value[0]] = key_value[1]
                    
                    elif line.startswith('2_visualid_') and current_unit is not None:
                        current_unit['visualid'] = line[11:]
                    
                    elif line.startswith('2_tname_') and current_unit is not None:
                        tname = line[8:]
                        if self.find_ssid_for_tname(tname):
                            pending_tname = tname
                            current_unit_tnames[tname] = ''
                        else:
                            pending_tname = None
                    
                    elif line.startswith('2_strgalt_fus_msbF_') and pending_tname and current_unit is not None:
                        current_unit_tnames[pending_tname] = line[19:]
                        pending_tname = None
                    
                    elif (line.startswith('2_sstrlot_') or line.startswith('2_sstrwafer_') or
                          line.startswith('2_sstrxloc_') or line.startswith('2_sstryloc_')):
                        ssid, value = self.extract_ssid_and_value_from_line(line)
                        if ssid and current_unit is not None:
                            if ssid not in current_unit_ult_lines:
                                current_unit_ult_lines[ssid] = []
                            current_unit_ult_lines[ssid].append(line)
                    
                    elif line.startswith('2_') and current_unit is not None:
                        key_value = line[2:].split('_', 1)
                        if len(key_value) == 2 and key_value[0] in current_unit:
                            current_unit[key_value[0]] = key_value[1]
                        
                        if not line.startswith('2_strgalt_fus_msbF_') and not line.startswith('2_tname_'):
                            pending_tname = None
            
            # Process last unit
            if current_unit is not None:
                current_unit['ult_data'] = self.parse_ult_data_for_unit(current_unit_ult_lines)
                current_unit['tname_values'] = current_unit_tnames.copy()
                units.append(current_unit)
        
        except Exception as e:
            print(f"❌ Error reading ITF file {itf_file_path}: {e}")
            return None, None
        
        return header_data, units
    
    def create_visualid_ssid_ult_tname_rows(self, units: List[Dict[str, Any]], header_data: Dict[str, Any], filename: str) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, int]]:
        """Create individual TNAME-VALUE rows."""
        rows = []
        all_ssids = set()
        tname_mapping_stats = defaultdict(int)
        
        units_by_visualid = defaultdict(list)
        for unit in units:
            visualid = unit.get('visualid')
            if visualid:
                units_by_visualid[visualid].append(unit)
        
        for visualid, unit_list in units_by_visualid.items():
            combined_ult_data = {}
            combined_tname_values = {}
            base_unit = unit_list[0]
            
            for unit in unit_list:
                combined_tname_values.update(unit.get('tname_values', {}))
                for ssid, ult_string in unit.get('ult_data', {}).items():
                    if ssid not in combined_ult_data:
                        combined_ult_data[ssid] = ult_string
                        all_ssids.add(ssid)
            
            for tname, tname_value in combined_tname_values.items():
                result = self.find_ssid_for_tname(tname)
                if result:
                    domain, register, mapped_ssid = result
                    ult_string = combined_ult_data.get(mapped_ssid, '')
                    
                    row = {
                        'filename': filename, 'visualid': visualid, 'SSID': mapped_ssid,
                        'ULT': ult_string, 'TNAME': tname, 'TNAME_VALUE': tname_value,
                        'Domain': domain, 'Register': register
                    }
                    
                    row.update(header_data)
                    unit_data = {k: v for k, v in base_unit.items() if k not in ['ult_data', 'tname_values']}
                    row.update(unit_data)
                    
                    rows.append(row)
                    tname_mapping_stats[f"{mapped_ssid}:{tname}"] += 1
        
        return rows, all_ssids, tname_mapping_stats
    
    def create_fullstring_rows(self, all_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create fullstring rows by combining FD values."""
        grouped_data = defaultdict(lambda: {'tname_values': {}, 'base_info': None})
        
        for row in all_rows:
            tname = row['TNAME']
            base_tname = self.extract_base_tname(tname)
            fd_number = self.extract_fd_number(tname)
            
            key = (row['visualid'], row['SSID'], base_tname)
            grouped_data[key]['tname_values'][fd_number] = row['TNAME_VALUE']
            
            if grouped_data[key]['base_info'] is None:
                base_info = row.copy()
                base_info['TNAME'] = base_tname
                grouped_data[key]['base_info'] = base_info
        
        fullstring_rows = []
        for (visualid, ssid, base_tname), data in grouped_data.items():
            base_info = data['base_info']
            tname_values = data['tname_values']
            
            sorted_fd_numbers = sorted(tname_values.keys())
            combined_value = ''.join(tname_values[fd_num] for fd_num in sorted_fd_numbers)
            
            fullstring_row = base_info.copy()
            fullstring_row.update({
                'TNAME_VALUE': combined_value,
                'FD_Count': len(tname_values),
                'FD_Numbers': ','.join(map(str, sorted_fd_numbers))
            })
            
            fullstring_rows.append(fullstring_row)
        
        return fullstring_rows
    
    def process_itf_files(self, ituff_dir: Path, output_dir: Path, fusefilename: str, 
                         lotname: str = None, location: str = None) -> bool:
        """Process all ITF files in the directory."""
        print("🔄 Processing ITF files...")
        
        itf_files = self.find_itf_files(ituff_dir)
        if not itf_files:
            print("⚠️  No ITF files found")
            return False
        
        all_rows = []
        all_ssids = set()
        
        for itf_file in itf_files:
            print(f"\n  Processing: {itf_file.name}")
            
            header_data, units = self.extract_itf_data(itf_file)
            if header_data is None or units is None:
                print(f"  ❌ Failed to extract data")
                continue
            
            valid_units = [unit for unit in units if unit.get('visualid')]
            print(f"    Found {len(units)} total units, {len(valid_units)} with visualID")
            
            total_matching_tnames = sum(len(unit.get('tname_values', {})) for unit in valid_units)
            print(f"    Found {total_matching_tnames} matching TNAMEs")
            
            rows, file_ssids, tname_stats = self.create_visualid_ssid_ult_tname_rows(
                valid_units, header_data, itf_file.name
            )
            
            all_rows.extend(rows)
            all_ssids.update(file_ssids)
            
            print(f"    Generated {len(rows)} TNAME-VALUE rows")
        
        if not all_rows:
            print("\n⚠️  No matching TNAMEs found")
            return False
        
        # Export individual rows CSV
        if lotname and location:
            suffix = f"{lotname}_{location}"
        else:
            suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
        individual_csv = output_dir / f"itf_tname_value_rows_{fusefilename}_{suffix}.csv"
        
        fieldnames = [
            'visualid', 'SSID', 'ULT', 'TNAME', 'TNAME_VALUE', 'Domain', 'Register', 'filename',
            'lotid', 'sspec', 'prgnm', 'lcode', 'sysid', 'facid', 'tempr',
            'prtnm', 'thermalhdid', 'dvtststdt', 'socket', 'tstordnum', 'tiuid',
            'eqpprtid', 'siteid', 'prttesterid', 'tiuprscdid', 'subflstpid', 'binn', 'curfbin', 'curibin'
        ]
        
        self._write_itf_csv(all_rows, individual_csv, fieldnames)
        print(f"\n✅ ITF individual rows CSV created: {individual_csv.name}")
        print(f"   Total TNAME-VALUE rows: {len(all_rows)}")
        
        # Create and export fullstring rows
        fullstring_rows = self.create_fullstring_rows(all_rows)
        fullstring_csv = output_dir / f"itf_tname_value_rows_fullstring_{fusefilename}_{suffix}.csv"
        
        fullstring_fieldnames = fieldnames[:7] + ['FD_Count', 'FD_Numbers'] + fieldnames[7:]
        
        self._write_itf_csv(fullstring_rows, fullstring_csv, fullstring_fieldnames)
        print(f"✅ ITF fullstring CSV created: {fullstring_csv.name}")
        print(f"   Total fullstring rows: {len(fullstring_rows)}")
        
        return True
    
    def _write_itf_csv(self, rows: List[Dict[str, Any]], output_file: Path, fieldnames: List[str]) -> None:
        """Write ITF data to CSV file."""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in rows:
                    output_row = {field: row.get(field, None) for field in fieldnames}
                    writer.writerow(output_row)
        except Exception as e:
            print(f"❌ Error writing CSV: {e}")
