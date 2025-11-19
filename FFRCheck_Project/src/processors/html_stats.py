"""HTML Statistics Report Generator with structured statsData object (matches reference format)."""
from pathlib import Path
from datetime import datetime
import csv
import json
from collections import Counter, defaultdict


class HTMLStatsGenerator:
    """Generates interactive HTML statistics report with structured statsData object."""
    
    def __init__(self, output_dir, fusefilename):
        self.output_dir = Path(output_dir)
        self.fusefilename = fusefilename
        
    def _read_csv_rows(self, csv_file):
        """Read CSV file and return list of row dictionaries."""
        if not csv_file.exists():
            return []
        
        rows = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows
    
    def _clean_bom(self, row_dict):
        """Remove BOM from dictionary keys and create cleaned dict."""
        cleaned = {}
        for key, value in row_dict.items():
            clean_key = key.replace('\ufeff', '')
            cleaned[clean_key] = value
        return cleaned
    
    def _build_ube_stats(self, ube_rows):
        """Build UBE statistics section."""
        if not ube_rows:
            return {}
        
        # Clean BOM from rows
        ube_rows = [self._clean_bom(row) for row in ube_rows]
        
        ref_levels = Counter(row.get('ref_level', '') for row in ube_rows if row.get('ref_level'))
        mdpositions = Counter(row.get('MDPOSITION', 'No MDPOSITION') for row in ube_rows)
        # Check for visualid (lowercase) or visualID (camelCase)
        visual_ids = set(
            row.get('visualid', '') or row.get('visualID', '') 
            for row in ube_rows 
            if row.get('visualid') or row.get('visualID')
        )
        ults = set(row.get('ULT', '') for row in ube_rows if row.get('ULT'))
        tokens = set(row.get('token_name', '') for row in ube_rows if row.get('token_name'))
        
        # Filter out empty MDPOSITION
        mdpositions_filtered = {k: v for k, v in mdpositions.items() if k and k != 'No MDPOSITION'}
        
        return {
            "total_entries": len(ube_rows),
            "unique_visual_ids": len(visual_ids),
            "unique_ults": len(ults),
            "unique_ref_levels": len(ref_levels),
            "unique_tokens": len(tokens),
            "unique_mdpositions": len(mdpositions_filtered),
            "ref_level_breakdown": dict(ref_levels),
            "mdposition_breakdown": dict(mdpositions)
        }
    
    def _build_xml_stats(self, mtlolf_rows):
        """Build XML statistics section with categorized tokens."""
        if not mtlolf_rows:
            return {}
        
        # Clean BOM from rows
        mtlolf_rows = [self._clean_bom(row) for row in mtlolf_rows]
        
        # Extract just the MTL fields (XML tokens) - KEEP _MTL SUFFIX
        tokens = []
        for row in mtlolf_rows:
            token = {}
            for key, value in row.items():
                if key.endswith('_MTL'):
                    # Convert field_name_seq_MTL to int
                    if key == 'field_name_seq_MTL':
                        try:
                            token[key] = int(value) if value else 1
                        except (ValueError, TypeError):
                            token[key] = 1
                    else:
                        token[key] = value
            if token:
                tokens.append(token)
        
        # Categorize tokens (use the actual field names without _MTL for counting)
        by_register = Counter(t.get('fuse_register_MTL', '') for t in tokens if t.get('fuse_register_MTL'))
        by_module = Counter(t.get('module_MTL', '') for t in tokens if t.get('module_MTL'))
        by_upload = Counter(t.get('first_socket_upload_MTL', '') for t in tokens if t.get('first_socket_upload_MTL'))
        
        # Group token details by all categories (KEEP _MTL SUFFIX in tokens)
        token_details_by_register = defaultdict(list)
        token_details_by_module = defaultdict(list)
        token_details_by_upload = defaultdict(list)
        
        for token in tokens:
            register = token.get('fuse_register_MTL', '')
            if register:
                token_details_by_register[register].append(token)
            
            module = token.get('module_MTL', '')
            if module:
                token_details_by_module[module].append(token)
            
            upload = token.get('first_socket_upload_MTL', '')
            if upload:
                token_details_by_upload[upload].append(token)
        
        token_names = set(t.get('token_name_MTL', '') for t in tokens if t.get('token_name_MTL'))
        
        return {
            "total_records": len(tokens),
            "total_tokens": len(tokens),
            "unique_token_names": len(token_names),
            "total_fields": len(tokens),
            "categorized_tokens": {
                "by_fuse_register": dict(by_register),
                "by_module": dict(by_module),
                "by_first_socket_upload": dict(by_upload)
            },
            "token_details": {
                "by_fuse_register": dict(token_details_by_register),
                "by_module": dict(token_details_by_module),
                "by_first_socket_upload": dict(token_details_by_upload)
            }
        }
    
    def _build_matching_stats(self, mtlolf_rows):
        """Build matching statistics section."""
        if not mtlolf_rows:
            return {}
        
        # Clean BOM from rows
        mtlolf_rows = [self._clean_bom(row) for row in mtlolf_rows]
        
        total = len(mtlolf_rows)
        register_matches = sum(1 for row in mtlolf_rows if row.get('register_match') == 'match')
        fusegroup_matches = sum(1 for row in mtlolf_rows if row.get('fusegroup_match') == 'match')
        fusename_matches = sum(1 for row in mtlolf_rows if row.get('fusename_match') == 'match')
        
        fusegroup_na = sum(1 for row in mtlolf_rows if row.get('fusegroup_match') == 'N/A')
        fusename_na = sum(1 for row in mtlolf_rows if row.get('fusename_match') == 'N/A')
        
        # Collect mismatch details
        register_mismatches = []
        fusegroup_mismatches = []
        fusename_mismatches = []
        
        for row in mtlolf_rows:
            if row.get('register_match') == 'mismatch':
                register_mismatches.append({
                    "token_name_MTL": row.get('token_name_MTL', ''),
                    "fuse_register_MTL": row.get('fuse_register_MTL', ''),
                    "RegisterName_fuseDef": row.get('RegisterName_fuseDef', '')
                })
            if row.get('fusegroup_match') == 'mismatch':
                fusegroup_mismatches.append({
                    "token_name_MTL": row.get('token_name_MTL', ''),
                    "fuse_name_MTL": row.get('fuse_name_MTL', ''),
                    "FuseGroup_Name_fuseDef": row.get('FuseGroup_Name_fuseDef', '')
                })
            if row.get('fusename_match') == 'mismatch':
                fusename_mismatches.append({
                    "token_name_MTL": row.get('token_name_MTL', ''),
                    "field_name_MTL": row.get('field_name_MTL', ''),
                    "module_MTL": row.get('module_MTL', ''),
                    "fuse_register_MTL": row.get('fuse_register_MTL', ''),
                    "fuse_name_MTL": row.get('fuse_name_MTL', ''),
                    "first_socket_upload_MTL": row.get('first_socket_upload_MTL', ''),
                    "ssid_MTL": row.get('ssid_MTL', ''),
                    "ref_level_MTL": row.get('ref_level_MTL', '')
                })
        
        # Build per-register mismatch summary
        per_register_mismatches = {}
        register_tokens = defaultdict(list)
        register_stats = defaultdict(lambda: {
            "register_mismatches": 0,
            "fusegroup_mismatches": 0,
            "fusename_mismatches": 0,
            "total_tokens": 0,
            "mismatch_tokens": []
        })
        
        for row in mtlolf_rows:
            register = row.get('fuse_register_MTL', 'Unknown')
            register_stats[register]["total_tokens"] += 1
            
            if row.get('register_match') == 'mismatch':
                register_stats[register]["register_mismatches"] += 1
                register_stats[register]["mismatch_tokens"].append(row)
            if row.get('fusegroup_match') == 'mismatch':
                register_stats[register]["fusegroup_mismatches"] += 1
            if row.get('fusename_match') == 'mismatch':
                register_stats[register]["fusename_mismatches"] += 1
        
        per_register_mismatches = dict(register_stats)
        
        return {
            "total_rows": total,
            "register_matches": register_matches,
            "fusegroup_matches": fusegroup_matches,
            "fusename_matches": fusename_matches,
            "fusegroup_na": fusegroup_na,
            "fusename_na": fusename_na,
            "mismatch_details": {
                "register_mismatches": register_mismatches,
                "fusegroup_mismatches": fusegroup_mismatches,
                "fusename_mismatches": fusename_mismatches
            },
            "per_register_mismatches": per_register_mismatches
        }
    
    def _build_dff_stats(self, dff_rows):
        """Build DFF check statistics section."""
        if not dff_rows:
            return {}
        
        # Clean BOM from rows
        dff_rows = [self._clean_bom(row) for row in dff_rows]
        
        visual_ids = set(row.get('visual_id', '') for row in dff_rows if row.get('visual_id'))
        rows_with_data = sum(1 for row in dff_rows if any(v for k, v in row.items() if k != 'visual_id'))
        
        # Count missing and invalid tokens per register
        missing_per_register = defaultdict(int)
        invalid_per_register = defaultdict(int)
        
        for row in dff_rows:
            for key, value in row.items():
                if key != 'visual_id' and value:
                    if 'missing' in value.lower():
                        missing_per_register[key] += 1
                    elif 'invalid' in value.lower():
                        invalid_per_register[key] += 1
        
        return {
            "total_rows": len(dff_rows),
            "visual_ids": len(visual_ids),
            "rows_with_data": rows_with_data,
            "missing_tokens_per_register": dict(missing_per_register),
            "invalid_tokens_per_register": dict(invalid_per_register)
        }
    
    def _build_itf_stats(self, itf_tname_rows, itf_fullstring_rows):
        """Build ITF statistics section."""
        # Clean BOM from rows
        itf_tname_rows = [self._clean_bom(row) for row in itf_tname_rows]
        itf_fullstring_rows = [self._clean_bom(row) for row in itf_fullstring_rows]
        
        ssids = set(row.get('SSID', '') for row in itf_tname_rows if row.get('SSID'))
        # Check for visualid (lowercase), visualID (camelCase), or Visual ID (with space)
        visual_ids = set(
            row.get('visualid', '') or row.get('visualID', '') or row.get('Visual ID', '') 
            for row in itf_tname_rows 
            if row.get('visualid') or row.get('visualID') or row.get('Visual ID')
        )
        ssid_breakdown = Counter(row.get('SSID', '') for row in itf_tname_rows if row.get('SSID'))
        
        # Count unique files from fullstring (assuming visual ID represents files)
        files = set(
            row.get('visualid', '') or row.get('visualID', '') or row.get('Visual ID', '') 
            for row in itf_fullstring_rows 
            if row.get('visualid') or row.get('visualID') or row.get('Visual ID')
        )
        
        return {
            "total_files": len(files) if files else 1,
            "unique_visual_ids": len(visual_ids),
            "total_tname_rows": len(itf_tname_rows),
            "total_fullstring_rows": len(itf_fullstring_rows),
            "unique_ssids": len(ssids),
            "ssid_breakdown": dict(ssid_breakdown)
        }
    
    def _build_sspec_stats(self, sspec_rows):
        """Build Sspec breakdown statistics section."""
        if not sspec_rows:
            return {}
        
        # Clean BOM from rows
        sspec_rows = [self._clean_bom(row) for row in sspec_rows]
        
        registers = set(row.get('RegisterName', '') for row in sspec_rows if row.get('RegisterName'))
        fuse_names = set(row.get('Fuse_Name_fuseDef', '') for row in sspec_rows if row.get('Fuse_Name_fuseDef'))
        
        # Detect all QDF columns (e.g., L2FW_binaryValue, L2FW_hexValue, GQDF_binaryValue, etc.)
        qdfs = set()
        if sspec_rows:
            sample_row = sspec_rows[0]
            for key in sample_row.keys():
                if '_binaryValue' in key or '_hexValue' in key:
                    qdf = key.split('_')[0]
                    qdfs.add(qdf)
        
        # Build register statistics per QDF
        register_stats = defaultdict(lambda: defaultdict(lambda: {
            "valid_extractions": 0,
            "valid_hex": 0,
            "failed_hex": 0,
            "fuse_definitions": 0,
            "bit_analysis": {"register_size": 0, "static_bits": 0, "dynamic_bits": 0, "sort_bits": 0},
            "total_bit_length": 0,
            "vf_heap_unused_bit_length": 0
        }))
        
        # Track register size per register per QDF
        register_sizes = defaultdict(lambda: defaultdict(int))
        
        for row in sspec_rows:
            register = row.get('RegisterName', '')
            if not register:
                continue
            
            # Get bit_length for register size calculation
            try:
                bit_length = int(row.get('bit_length', 0))
            except (ValueError, TypeError):
                bit_length = 0
            
            # Process each QDF found in this row
            for qdf in qdfs:
                binary_key = f'{qdf}_binaryValue'
                hex_key = f'{qdf}_hexValue'
                
                binary_val = row.get(binary_key, '')
                hex_val = row.get(hex_key, '')
                
                # Only process if this QDF has data for this row
                if binary_val or hex_val:
                    stats = register_stats[register][qdf]
                    stats["fuse_definitions"] += 1
                    stats["total_bit_length"] += bit_length
                    
                    # Count valid extractions (has hex value)
                    if hex_val:
                        stats["valid_extractions"] += 1
                        if hex_val.upper() not in ['FAILED', 'Q']:
                            stats["valid_hex"] += 1
                        else:
                            stats["failed_hex"] += 1
                    
                    # Track "VF_Heap_Unused" specifically
                    fuse_group = row.get('FuseGroup_Name_fuseDef', '')
                    if 'VF_Heap_Unused' in fuse_group or 'Heap_Unused' in fuse_group:
                        stats["vf_heap_unused_bit_length"] += bit_length
                    
                    # Accumulate register size for this QDF
                    register_sizes[register][qdf] = max(register_sizes[register][qdf], stats["total_bit_length"])
                    
                    # Bit analysis based on binary value patterns
                    if binary_val:
                        if binary_val.startswith('b'):
                            binary_val = binary_val[1:]  # Remove 'b' prefix
                        
                        # Count bit types
                        static_0_or_1 = sum(1 for c in binary_val if c in '01')
                        dynamic_m = sum(1 for c in binary_val if c == 'm')
                        sort_s = sum(1 for c in binary_val if c == 's')
                        
                        stats["bit_analysis"]["static_bits"] += static_0_or_1
                        stats["bit_analysis"]["dynamic_bits"] += dynamic_m
                        stats["bit_analysis"]["sort_bits"] += sort_s
        
        # Calculate percentages and finalize stats
        final_register_stats = {}
        for register, qdfs_dict in register_stats.items():
            final_register_stats[register] = {}
            for qdf, stats in qdfs_dict.items():
                total = stats["fuse_definitions"]
                if total > 0:
                    stats["valid_extractions_percent"] = round(100.0 * stats["valid_extractions"] / total, 1)
                    if stats["valid_extractions"] > 0:
                        stats["valid_hex_percent"] = round(100.0 * stats["valid_hex"] / stats["valid_extractions"], 1)
                        stats["failed_hex_percent"] = round(100.0 * stats["failed_hex"] / stats["valid_extractions"], 1)
                
                # Set register size
                stats["bit_analysis"]["register_size"] = register_sizes[register][qdf]
                
                # Calculate VF Heap Unused percentage
                if stats["bit_analysis"]["register_size"] > 0:
                    stats["vf_heap_unused_percentage"] = round(100.0 * stats["vf_heap_unused_bit_length"] / stats["bit_analysis"]["register_size"], 1)
                else:
                    stats["vf_heap_unused_percentage"] = 0.0
                
                final_register_stats[register][qdf] = stats
        
        return {
            "total_breakdown_rows": len(sspec_rows),
            "unique_registers": len(registers),
            "unique_fuse_names": len(fuse_names),
            "qdfs_processed": len(qdfs),
            "register_statistics": final_register_stats
        }
    
    def _build_statuscheck_stats(self, unit_data_rows):
        """Build StatusCheck statistics from S_UnitData_by_Fuse file."""
        if not unit_data_rows:
            return {}
        
        # Clean BOM from rows
        unit_data_rows = [self._clean_bom(row) for row in unit_data_rows]
        
        # Find all visual IDs
        visual_ids = set()
        for row in unit_data_rows:
            for key in row.keys():
                if key.endswith('_StatusCheck'):
                    vid = key.replace('_StatusCheck', '')
                    visual_ids.add(vid)
        
        if not visual_ids:
            return {}
        
        # Count StatusCheck values for each visual ID
        statuscheck_counts = {}
        for vid in visual_ids:
            status_col = f'{vid}_StatusCheck'
            counts = Counter(row.get(status_col, 'N/A') for row in unit_data_rows if row.get(status_col))
            statuscheck_counts[vid] = dict(counts)
        
        # Calculate overall statistics using first visual ID (all should be same)
        total_fuses = len(unit_data_rows)
        overall_counts = Counter()
        
        # Use first visual ID for overall counts
        if visual_ids:
            first_vid = sorted(visual_ids)[0]
            overall_counts = Counter(statuscheck_counts[first_vid])
        
        # Calculate percentages
        statuscheck_percentages = {}
        for status, count in overall_counts.items():
            statuscheck_percentages[status] = {
                "count": count,
                "percentage": round(100.0 * count / total_fuses, 1) if total_fuses > 0 else 0
            }
        
        # Build per-unit per-register breakdown
        per_unit_register_stats = {}
        for vid in visual_ids:
            status_col = f'{vid}_StatusCheck'
            register_stats = defaultdict(lambda: Counter())
            
            for row in unit_data_rows:
                register = row.get('RegisterName', row.get('Register', 'Unknown'))
                status = row.get(status_col, 'N/A')
                if status:
                    register_stats[register][status] += 1
            
            # Convert to regular dict and calculate percentages
            per_unit_register_stats[vid] = {}
            for register, counts in register_stats.items():
                total = sum(counts.values())
                per_unit_register_stats[vid][register] = {
                    'counts': dict(counts),
                    'total': total,
                    'percentages': {
                        status: round(100.0 * count / total, 1) if total > 0 else 0
                        for status, count in counts.items()
                    }
                }
        
        return {
            "total_fuses": total_fuses,
            "visual_ids": sorted(list(visual_ids)),
            "statuscheck_by_vid": statuscheck_counts,
            "overall_statuscheck": dict(overall_counts),
            "statuscheck_percentages": statuscheck_percentages,
            "per_unit_register_stats": per_unit_register_stats
        }
    
    def generate_html_report(self):
        """Generate complete interactive HTML statistics report.
        
        Returns:
            Path to the generated HTML file
        """
        html_file = self.output_dir / f"HTML_Statistics_Report_{self.fusefilename}.html"
        
        # Find UBE CSV file (could have different naming pattern)
        ube_csv = None
        for file in self.output_dir.glob("I_Report_UBE*.csv"):
            ube_csv = file
            break
        
        # Find ITF CSV files (could have timestamp)
        itf_tname_csv = None
        itf_fullstring_csv = None
        for file in self.output_dir.glob("*ITF_Rows_*.csv"):
            if "fullstring" not in file.name:
                itf_tname_csv = file
        for file in self.output_dir.glob("*ITF_FullString_*.csv"):
            itf_fullstring_csv = file
        # Fallback to expected names
        if not itf_tname_csv:
            itf_tname_csv = self.output_dir / f"x{self.fusefilename}_itf_tname_value_rows.csv"
        if not itf_fullstring_csv:
            itf_fullstring_csv = self.output_dir / f"x{self.fusefilename}_itf_tname_value_rows_fullstring.csv"
        
        # Find sspec CSV file (could have L2FW prefix)
        sspec_csv = None
        for file in self.output_dir.glob("S_SSPEC_Breakdown*.csv"):
            sspec_csv = file
            break
        if not sspec_csv:
            sspec_csv = self.output_dir / f"S_SSPEC_Breakdown_{self.fusefilename}.csv"
        
        # Find S_UnitData_by_Fuse CSV file (contains StatusCheck)
        unit_data_csv = None
        for file in self.output_dir.glob("S_UnitData_by_Fuse*.csv"):
            unit_data_csv = file
            break
        if not unit_data_csv:
            unit_data_csv = self.output_dir / f"S_UnitData_by_Fuse_{self.fusefilename}.csv"
        
        # Find raw MTL_OLF CSV file
        mtlolf_csv = None
        for file in self.output_dir.glob("I_Report_MTL_OLF*.csv"):
            mtlolf_csv = file
            break
        
        # Define CSV file paths
        csv_files = {
            'ube': ube_csv if ube_csv else self.output_dir / f"I_Report_UBE_{self.fusefilename}.csv",
            'mtlolf': mtlolf_csv if mtlolf_csv else self.output_dir / f"I_Report_MTL_OLF_{self.fusefilename}.csv",
            'mtlolf_check': self.output_dir / f"V_Report_FuseDef_vs_MTL_OLF_{self.fusefilename}.csv",
            'dff_check': self.output_dir / f"V_Report_DFF_UnitData_{self.fusefilename}.csv",
            'itf_rows': itf_tname_csv,
            'itf_fullstring': itf_fullstring_csv,
            'sspec_breakdown': sspec_csv,
            'unit_data': unit_data_csv
        }
        
        # Load CSV data
        print("Loading CSV files for HTML report...")
        ube_rows = self._read_csv_rows(csv_files['ube'])
        mtlolf_xml_rows = self._read_csv_rows(csv_files['mtlolf'])  # Raw XML data
        mtlolf_check_rows = self._read_csv_rows(csv_files['mtlolf_check'])  # Matching data
        dff_rows = self._read_csv_rows(csv_files['dff_check'])
        itf_tname_rows = self._read_csv_rows(csv_files['itf_rows'])
        itf_fullstring_rows = self._read_csv_rows(csv_files['itf_fullstring'])
        sspec_rows = self._read_csv_rows(csv_files['sspec_breakdown'])
        unit_data_rows = self._read_csv_rows(csv_files['unit_data'])
        
        # Build statsData object
        print("Building statsData object...")
        stats_data = {
            "overview": {
                "ube_entries": len(ube_rows),
                "xml_records": len(mtlolf_xml_rows),
                "dff_rows": len(dff_rows),
                "itf_tname_rows": len(itf_tname_rows),
                "itf_fullstring_rows": len(itf_fullstring_rows),
                "sspec_breakdown_rows": len(sspec_rows),
                "unit_data_rows": len(unit_data_rows)
            },
            "ube": self._build_ube_stats(ube_rows),
            "xml": self._build_xml_stats(mtlolf_xml_rows),
            "matching": self._build_matching_stats(mtlolf_check_rows),
            "dff": self._build_dff_stats(dff_rows),
            "itf": self._build_itf_stats(itf_tname_rows, itf_fullstring_rows),
            "sspec": self._build_sspec_stats(sspec_rows),
            "statuscheck": self._build_statuscheck_stats(unit_data_rows)
        }
        
        # Prepare breakdown data for sspec download functionality
        breakdown_data = [self._clean_bom(row) for row in sspec_rows]
        
        # Generate HTML with embedded statsData and breakdownData
        html_content = self._generate_html_template(stats_data, breakdown_data)
        
        print(f"Writing HTML file: {html_file}")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(html_file)
    
    def _generate_html_template(self, stats_data, breakdown_data):
        """Generate the full HTML template with embedded statsData object and breakdownData."""
        
        # Extract summary counts for display
        ube_count = stats_data.get('ube', {}).get('total_entries', 0)
        xml_count = stats_data.get('xml', {}).get('total_records', 0)
        matching_total = stats_data.get('matching', {}).get('total_rows', 0)
        dff_count = stats_data.get('dff', {}).get('total_rows', 0)
        itf_tname = stats_data.get('itf', {}).get('total_tname_rows', 0)
        itf_fullstring = stats_data.get('itf', {}).get('total_fullstring_rows', 0)
        sspec_count = stats_data.get('sspec', {}).get('total_breakdown_rows', 0)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FFR Check Statistics - {self.fusefilename}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px;
            border-radius: 8px 8px 0 0;
        }}
        
        .header h1 {{
            font-size: 36px;
            margin-bottom: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .header p {{
            opacity: 0.95;
            font-size: 16px;
            line-height: 1.6;
        }}
        
        .nav-tabs {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .nav-tab {{
            padding: 12px 24px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 15px;
            font-weight: 500;
            color: #333;
        }}
        
        .nav-tab:hover {{
            background: #e3f2fd;
            border-color: #2196F3;
        }}
        
        .nav-tab.active {{
            background: #2196F3;
            color: white;
            border-color: #2196F3;
        }}
        
        .tab-content {{
            display: none;
            padding: 30px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            font-size: 16px;
            opacity: 0.95;
            margin-bottom: 12px;
            font-weight: 500;
            letter-spacing: 0.3px;
        }}
        
        .summary-card .value {{
            font-size: 42px;
            font-weight: bold;
            line-height: 1.2;
        }}
        
        .data-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .data-section h2 {{
            color: #2c3e50;
            margin-bottom: 18px;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .data-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .data-item {{
            background: white;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
        }}
        
        .data-item strong {{
            display: block;
            color: #555;
            font-size: 14px;
            margin-bottom: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .data-item span {{
            font-size: 22px;
            color: #2c3e50;
            font-weight: bold;
            line-height: 1.4;
        }}
        
        .expandable {{
            background: white;
            margin-bottom: 10px;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
        }}
        
        .expandable-header {{
            padding: 15px;
            cursor: pointer;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            font-weight: bold;
            color: #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .expandable-header:hover {{
            background: #e3f2fd;
        }}
        
        .expandable-content {{
            display: none;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .expandable-content.active {{
            display: block;
        }}
        
        .mismatch-item {{
            background: #fff3e0;
            padding: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #ff9800;
            border-radius: 4px;
        }}
        
        .match-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .match-stat {{
            background: white;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            border: 1px solid #e0e0e0;
        }}
        
        .match-stat.success {{
            border-left: 4px solid #4caf50;
        }}
        
        .match-stat.warning {{
            border-left: 4px solid #ff9800;
        }}
        
        .match-stat.error {{
            border-left: 4px solid #f44336;
        }}
        
        .register-section {{
            margin-bottom: 20px;
        }}
        
        .register-header {{
            background: #e3f2fd;
            padding: 10px 15px;
            border-radius: 4px;
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        
        th, td {{
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
            font-size: 14px;
            line-height: 1.5;
        }}
        
        th {{
            background: #e8eaf6;
            font-weight: 600;
            color: #2c3e50;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .filter-section {{
            margin-bottom: 20px;
            padding: 18px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .filter-section input {{
            width: 100%;
            padding: 12px 14px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 15px;
            line-height: 1.5;
        }}
        
        .footer {{
            text-align: center;
            padding: 25px;
            color: #555;
            font-size: 14px;
            border-top: 2px solid #e0e0e0;
            line-height: 1.6;
        }}
        
        /* Interactive Section Styles */
        .section-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            cursor: pointer;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
            border: 1px solid #e0e0e0;
        }}
        
        .section-header:hover {{
            background: #e3f2fd;
            border-color: #3498db;
        }}
        
        .section-title {{
            font-weight: 600;
            color: #2c3e50;
            font-size: 18px;
            line-height: 1.4;
        }}
        
        .section-badge {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .badge {{
            padding: 6px 14px;
            border-radius: 14px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .badge-info {{
            background: #3498db;
            color: white;
        }}
        
        .badge-warning {{
            background: #f39c12;
            color: white;
        }}
        
        .badge-danger {{
            background: #e74c3c;
            color: white;
        }}
        
        .expandable-content.show {{
            display: block !important;
            animation: slideDown 0.3s ease;
        }}
        
        @keyframes slideDown {{
            from {{
                opacity: 0;
                max-height: 0;
            }}
            to {{
                opacity: 1;
                max-height: 2000px;
            }}
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2980b9);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.85em;
            transition: width 0.5s ease;
        }}
        
        .download-btn {{
            padding: 8px 16px;
            background: #27ae60;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .download-btn:hover {{
            background: #229954;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .qdf-download-btn {{
            padding: 7px 14px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }}
        
        .qdf-download-btn:hover {{
            background: #2980b9;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin-top: 15px;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        .data-table th {{
            background: #34495e;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        
        .data-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #ecf0f1;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .data-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .alert {{
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .alert-info {{
            background: #d1ecf1;
            border-left: 4px solid #0c5460;
            color: #0c5460;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-left: 4px solid #856404;
            color: #856404;
        }}
        
        .alert h4 {{
            margin-bottom: 10px;
        }}
        
        .alert ul {{
            margin-left: 20px;
        }}
        
        .per-register-mismatch {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }}
        
        .register-mismatch-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        
        .register-stat-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .register-stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .register-stat-label {{
            color: #555;
            font-size: 14px;
            margin-top: 5px;
            font-weight: 500;
        }}
        
        .register-analysis-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        .register-analysis-table th {{
            background: #2c3e50;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }}
        
        .register-analysis-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .register-analysis-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .icon {{
            margin-right: 8px;
        }}
        
        .stat-subdescription {{
            color: #95a5a6;
            font-size: 0.85em;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 FFR Check Statistics Report</h1>
            <p>Fuse Filename: {self.fusefilename}</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('overview')">📊 Overview</button>
            <button class="nav-tab" onclick="showTab('ube')">📁 UBE Statistics</button>
            <button class="nav-tab" onclick="showTab('xml')">📄 XML Tokens</button>
            <button class="nav-tab" onclick="showTab('matching')">🔗 Matching Analysis</button>
            <button class="nav-tab" onclick="showTab('dff')">🔍 DFF Check</button>
            <button class="nav-tab" onclick="showTab('statuscheck')">✅ DFF-ITF StatusCheck</button>
            <button class="nav-tab" onclick="showTab('unitsummary')">📊 Unit Summary</button>
            <button class="nav-tab" onclick="showTab('itf')">📋 ITF Data</button>
            <button class="nav-tab" onclick="showTab('sspec')">🔧 Sspec Breakdown</button>
        </div>
        
        <div id="overview" class="tab-content active">
            <div class="summary-section">
                <h2>📈 Processing Summary</h2>
                <div class="summary-grid" id="overview-summary"></div>
            </div>
        </div>
        
        <div id="ube" class="tab-content"><h2>📄 UBE File Analysis</h2><div id="ube-content"></div></div>
        <div id="xml" class="tab-content"><h2>📄 MTL-OLF Analysis</h2><div id="xml-content"></div></div>
        <div id="matching" class="tab-content"><h2>🔗 Matching Analysis</h2><div id="matching-content"></div></div>
        <div id="dff" class="tab-content"><h2>🎯 DFF MTL-OLF Analysis</h2><div id="dff-content"></div></div>
        <div id="statuscheck" class="tab-content"><h2>✅ DFF-ITF StatusCheck Analysis</h2><div id="statuscheck-content"></div></div>
        <div id="unitsummary" class="tab-content"><h2>📊 Per-Unit StatusCheck Summary</h2><div id="unitsummary-content"></div></div>
        <div id="sspec" class="tab-content"><h2>🧬 SSPEC Breakdown Analysis</h2><div id="sspec-content"></div></div>
        <div id="itf" class="tab-content"><h2>📋 ITF Analysis</h2><div id="itf-content"></div></div>
        
        <div class="footer">
            <p>FFR Check Statistics Report | Generated by FFRCheck Tool</p>
        </div>
    </div>
    
    <script>
        // Embedded structured statsData object and breakdownData (matches reference format)
        let statsData = {json.dumps(stats_data)};
        let breakdownData = {json.dumps(breakdown_data)};

        function showTab(tabName) {{
                    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
                    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                    loadTabContent(tabName);
                }}

                function loadTabContent(tabName) {{
                    const contentMap = {{
                        'overview': loadOverviewContent,
                        'ube': loadUBEContent,
                        'xml': loadXMLContent,
                        'matching': loadMatchingContent,
                        'dff': loadDFFContent,
                        'statuscheck': loadStatusCheckContent,
                        'unitsummary': loadUnitSummaryContent,
                        'sspec': loadSspecContent,
                        'itf': loadITFContent
                    }};
                    if (contentMap[tabName]) contentMap[tabName]();
                }}

                function loadOverviewContent() {{
                    const summaryDiv = document.getElementById('overview-summary');
                    let summaryHTML = '';

                    if (statsData.overview) {{
                        Object.entries(statsData.overview).forEach(([key, value]) => {{
                            summaryHTML += `
                                <div class="summary-item">
                                    <div class="number">${{value}}</div>
                                    <div class="label">${{key.replace(/_/g, ' ').toUpperCase()}}</div>
                                </div>
                            `;
                        }});
                    }}
                    summaryDiv.innerHTML = summaryHTML;
                }}

                function loadUBEContent() {{
                    const contentDiv = document.getElementById('ube-content');
                    if (!statsData.ube) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No UBE data available</div>';
                        return;
                    }}

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total Entries</h3>
                                <div class="stat-value">${{statsData.ube.total_entries || 0}}</div>
                                <div class="stat-description">Total UBE entries processed</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">👁️</span>Visual IDs</h3>
                                <div class="stat-value">${{statsData.ube.unique_visual_ids || 0}}</div>
                                <div class="stat-description">Unique visual identifiers</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🏷️</span>Tokens</h3>
                                <div class="stat-value">${{statsData.ube.unique_tokens || 0}}</div>
                                <div class="stat-description">Unique token names</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">📍</span>MDPOSITION</h3>
                                <div class="stat-value">${{statsData.ube.unique_mdpositions || 0}}</div>
                                <div class="stat-description">Unique MDPOSITION values</div>
                            </div>
                        </div>
                    `;

                    if (statsData.ube.ref_level_breakdown) {{
                        html += createBreakdownSection('ref_level_breakdown', 'Breakdown by ref_level', statsData.ube.ref_level_breakdown);
                    }}

                    if (statsData.ube.mdposition_breakdown) {{
                        html += createBreakdownSection('mdposition_breakdown', 'Breakdown by MDPOSITION', statsData.ube.mdposition_breakdown);
                    }}

                    contentDiv.innerHTML = html;
                }}

                function loadXMLContent() {{
                    const contentDiv = document.getElementById('xml-content');
                    if (!statsData.xml) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No MTL-OLF data available</div>';
                        return;
                    }}

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📄</span>Total Records</h3>
                                <div class="stat-value">${{statsData.xml.total_records || 0}}</div>
                                <div class="stat-description">MTL-OLF records extracted</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🎯</span>Tokens</h3>
                                <div class="stat-value">${{statsData.xml.total_tokens || 0}}</div>
                                <div class="stat-description">Total tokens processed</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🏷️</span>Unique Token Names</h3>
                                <div class="stat-value">${{statsData.xml.unique_token_names || 0}}</div>
                                <div class="stat-description">Distinct token names</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">📁</span>Fields</h3>
                                <div class="stat-value">${{statsData.xml.total_fields || 0}}</div>
                                <div class="stat-description">Value decoder fields</div>
                            </div>
                        </div>
                    `;

                    if (statsData.xml.categorized_tokens) {{
                        html += '<div class="chart-container"><h3>📊 Token Analysis by Categories</h3>';

                        if (statsData.xml.categorized_tokens.by_fuse_register) {{
                            html += createDetailedCategorizedSection('by_fuse_register', 'By Fuse Register', 
                                statsData.xml.categorized_tokens.by_fuse_register, 
                                statsData.xml.token_details ? statsData.xml.token_details.by_fuse_register : {{}});
                        }}

                        if (statsData.xml.categorized_tokens.by_module) {{
                            html += createDetailedCategorizedSection('by_module', 'By Module', 
                                statsData.xml.categorized_tokens.by_module,
                                statsData.xml.token_details ? statsData.xml.token_details.by_module : {{}});
                        }}

                        if (statsData.xml.categorized_tokens.by_first_socket_upload) {{
                            html += createDetailedCategorizedSection('by_first_socket_upload', 'By First Socket Upload', 
                                statsData.xml.categorized_tokens.by_first_socket_upload,
                                statsData.xml.token_details ? statsData.xml.token_details.by_first_socket_upload : {{}});
                        }}

                        html += '</div>';
                    }}

                    contentDiv.innerHTML = html;
                }}

                function loadMatchingContent() {{
                    const contentDiv = document.getElementById('matching-content');
                    if (!statsData.matching) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No matching data available</div>';
                        return;
                    }}

                    const total = statsData.matching.total_rows || 0;
                    const registerMatches = statsData.matching.register_matches || 0;
                    const fusegroupMatches = statsData.matching.fusegroup_matches || 0;
                    const fusenameMatches = statsData.matching.fusename_matches || 0;

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total Rows</h3>
                                <div class="stat-value">${{total}}</div>
                                <div class="stat-description">Combined rows processed</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🎯</span>Register Matches</h3>
                                <div class="stat-value">${{registerMatches}}</div>
                                <div class="stat-description">${{total > 0 ? ((registerMatches/total)*100).toFixed(1) : 0}}% success rate</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">📁</span>FuseGroup Matches</h3>
                                <div class="stat-value">${{fusegroupMatches}}</div>
                                <div class="stat-description">${{total > 0 ? ((fusegroupMatches/total)*100).toFixed(1) : 0}}% success rate</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🔗</span>FuseName Matches</h3>
                                <div class="stat-value">${{fusenameMatches}}</div>
                                <div class="stat-description">${{total > 0 ? ((fusenameMatches/total)*100).toFixed(1) : 0}}% success rate</div>
                            </div>
                        </div>
                    `;

                    if (statsData.matching.mismatch_details) {{
                        html += '<div class="chart-container"><h3>⚠️ Mismatch Analysis</h3>';

                        html += '<div class="alert alert-warning">';
                        html += '<h4>📊 Overall Mismatch Summary</h4>';
                        html += '<ul>';
                        html += `<li><strong>Register Mismatches:</strong> ${{statsData.matching.mismatch_details.register_mismatches.length}} items</li>`;
                        html += `<li><strong>FuseGroup Mismatches:</strong> ${{statsData.matching.mismatch_details.fusegroup_mismatches.length}} items</li>`;
                        html += `<li><strong>FuseName Mismatches:</strong> ${{statsData.matching.mismatch_details.fusename_mismatches.length}} items</li>`;
                        html += '</ul>';
                        html += '</div>';

                        if (statsData.matching.per_register_mismatches) {{
                            html += '<h4>📋 Per-Register Mismatch Analysis</h4>';

                            Object.entries(statsData.matching.per_register_mismatches).forEach(([register, registerData]) => {{
                                html += `
                                    <div class="per-register-mismatch">
                                        <h4>📌 Register: ${{register}}</h4>
                                        <div class="register-mismatch-stats">
                                            <div class="register-stat-item">
                                                <div class="register-stat-number">${{registerData.register_mismatches}}</div>
                                                <div class="register-stat-label">Register Mismatches</div>
                                            </div>
                                            <div class="register-stat-item">
                                                <div class="register-stat-number">${{registerData.fusegroup_mismatches}}</div>
                                                <div class="register-stat-label">FuseGroup Mismatches</div>
                                            </div>
                                            <div class="register-stat-item">
                                                <div class="register-stat-number">${{registerData.fusename_mismatches}}</div>
                                                <div class="register-stat-label">FuseName Mismatches</div>
                                            </div>
                                            <div class="register-stat-item">
                                                <div class="register-stat-number">${{registerData.total_tokens}}</div>
                                                <div class="register-stat-label">Total Tokens</div>
                                            </div>
                                        </div>
                                        <div style="margin-top: 10px;">
                                            <button class="download-btn" onclick="downloadRegisterMismatchData('${{register}}', ${{JSON.stringify(registerData.mismatch_tokens).replace(/"/g, '&quot;')}})">
                                                📥 Download ${{register}} Mismatches
                                            </button>
                                        </div>
                                    </div>
                                `;
                            }});
                        }}

                        if (statsData.matching.mismatch_details.register_mismatches && 
                            statsData.matching.mismatch_details.register_mismatches.length > 0) {{
                            html += createMismatchTableSection('register_mismatches', 'Register Mismatches', 
                                statsData.matching.mismatch_details.register_mismatches);
                        }}

                        if (statsData.matching.mismatch_details.fusegroup_mismatches && 
                            statsData.matching.mismatch_details.fusegroup_mismatches.length > 0) {{
                            html += createMismatchTableSection('fusegroup_mismatches', 'FuseGroup Mismatches', 
                                statsData.matching.mismatch_details.fusegroup_mismatches);
                        }}

                        if (statsData.matching.mismatch_details.fusename_mismatches && 
                            statsData.matching.mismatch_details.fusename_mismatches.length > 0) {{
                            html += createMismatchTableSection('fusename_mismatches', 'FuseName Mismatches', 
                                statsData.matching.mismatch_details.fusename_mismatches);
                        }}

                        html += '</div>';
                    }}

                    contentDiv.innerHTML = html;
                }}

                function loadDFFContent() {{
                    const contentDiv = document.getElementById('dff-content');
                    if (!statsData.dff) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No DFF data available</div>';
                        return;
                    }}

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total Rows</h3>
                                <div class="stat-value">${{statsData.dff.total_rows || 0}}</div>
                                <div class="stat-description">DFF analysis rows</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">✅</span>Rows with Data</h3>
                                <div class="stat-value">${{statsData.dff.rows_with_data || 0}}</div>
                                <div class="stat-description">${{statsData.dff.total_rows > 0 ? ((statsData.dff.rows_with_data/(statsData.dff.total_rows))*100).toFixed(1) : 0}}% coverage</div>
                            </div>
                        </div>
                    `;

                    let totalMissingTokens = 0;
                    let totalInvalidTokens = 0;
                    let totalUnitsWithInvalid = 0;

                    if (statsData.dff.missing_tokens_per_register) {{
                        Object.values(statsData.dff.missing_tokens_per_register).forEach(tokens => {{
                            totalMissingTokens += tokens.length;
                        }});
                    }}

                    if (statsData.dff.invalid_tokens_per_register) {{
                        Object.values(statsData.dff.invalid_tokens_per_register).forEach(tokens => {{
                            totalInvalidTokens += tokens.length;
                            totalUnitsWithInvalid += tokens.reduce((sum, token) => sum + (token.invalid_count || 0), 0);
                        }});
                    }}

                    if (totalMissingTokens > 0 || totalInvalidTokens > 0) {{
                        html += `
                            <div class="missing-invalid-summary">
                                <h3>📋 Missing & Invalid Token Summary</h3>
                                <div class="summary-stats">
                                    <div class="summary-stat-card missing">
                                        <div class="summary-stat-number missing">${{totalMissingTokens}}</div>
                                        <div class="summary-stat-label">Missing Token Values</div>
                                    </div>
                                    <div class="summary-stat-card invalid">
                                        <div class="summary-stat-number invalid">${{totalInvalidTokens}}</div>
                                        <div class="summary-stat-label">Tokens with Invalid Values (-999)</div>
                                    </div>
                                    <div class="summary-stat-card invalid">
                                        <div class="summary-stat-number invalid">${{totalUnitsWithInvalid}}</div>
                                        <div class="summary-stat-label">Total Invalid Value Instances</div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }}

                    if (statsData.dff.missing_tokens_per_register) {{
                        html += '<div class="chart-container"><h3>⚠️ Missing Token Values by Register</h3>';

                        Object.entries(statsData.dff.missing_tokens_per_register).forEach(([register, missingTokens]) => {{
                            const registerId = `missing_tokens_${{register.replace(/[^a-zA-Z0-9]/g, '_')}}`;
                            html += `
                                <div class="section-header" onclick="toggleMismatchExpansion('${{registerId}}')">
                                    <span class="section-title" style="color: #e53e3e;">📌 ${{register}}</span>
                                    <div class="section-badge">
                                        <span class="badge badge-warning">${{missingTokens.length}} missing tokens</span>
                                        <button class="download-btn" onclick="event.stopPropagation(); downloadMissingTokensData('${{register}}', ${{JSON.stringify(missingTokens).replace(/"/g, '&quot;')}})">
                                            📥 Download CSV
                                        </button>
                                        <span id="${{registerId}}_arrow">▼</span>
                                    </div>
                                </div>
                                <div id="${{registerId}}_content" class="expandable-content">
                                    <div class="table-container">
                                        <table class="data-table">
                                            <thead>
                                                <tr>
                                                    <th>Token Name</th>
                                                    <th>Field Name</th>
                                                    <th>Module</th>
                                                    <th>SSID</th>
                                                    <th>Ref Level</th>
                                                    <th>First Socket Upload</th>
                                                    <th>Upload Process Step</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                            `;

                            missingTokens.forEach(token => {{
                                html += `
                                    <tr>
                                        <td title="${{token.token_name_MTL || ''}}">${{token.token_name_MTL || ''}}</td>
                                        <td title="${{token.field_name_MTL || ''}}">${{token.field_name_MTL || ''}}</td>
                                        <td title="${{token.module_MTL || ''}}">${{token.module_MTL || ''}}</td>
                                        <td title="${{token.ssid_MTL || ''}}">${{token.ssid_MTL || ''}}</td>
                                        <td title="${{token.ref_level_MTL || ''}}">${{token.ref_level_MTL || ''}}</td>
                                        <td title="${{token.first_socket_upload_MTL || ''}}">${{token.first_socket_upload_MTL || ''}}</td>
                                        <td title="${{token.upload_process_step_MTL || ''}}">${{token.upload_process_step_MTL || ''}}</td>
                                    </tr>
                                `;
                            }});

                            html += `
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            `;
                        }});

                        html += '</div>';
                    }}

                    if (statsData.dff.invalid_tokens_per_register) {{
                        html += '<div class="chart-container"><h3>❌ Invalid Token Values (-999) by Register</h3>';

                        Object.entries(statsData.dff.invalid_tokens_per_register).forEach(([register, invalidTokens]) => {{
                            const registerId = `invalid_tokens_${{register.replace(/[^a-zA-Z0-9]/g, '_')}}`;

                            const totalInvalidInRegister = invalidTokens.reduce((sum, token) => sum + (token.invalid_count || 0), 0);
                            const totalFusesInRegister = invalidTokens.reduce((sum, token) => sum + (token.total_fuses || 0), 0);

                            html += `
                                <div class="invalid-value-section">
                                    <div class="section-header" onclick="toggleMismatchExpansion('${{registerId}}')">
                                        <span class="section-title" style="color: #e53e3e;">📌 ${{register}}</span>
                                        <div class="section-badge">
                                            <span class="badge badge-danger">${{invalidTokens.length}} tokens with -999</span>
                                            <span class="badge badge-warning">${{totalInvalidInRegister}}/${{totalFusesInRegister}} invalid values</span>
                                            <button class="download-btn" onclick="event.stopPropagation(); downloadInvalidTokensData('${{register}}', ${{JSON.stringify(invalidTokens).replace(/"/g, '&quot;')}})">
                                                📥 Download CSV
                                            </button>
                                            <span id="${{registerId}}_arrow">▼</span>
                                        </div>
                                    </div>

                                    <div class="invalid-value-stats">
                                        <div class="invalid-stat-item">
                                            <div class="invalid-stat-number">${{invalidTokens.length}}</div>
                                            <div class="invalid-stat-label">Tokens with -999</div>
                                        </div>
                                        <div class="invalid-stat-item">
                                            <div class="invalid-stat-number">${{totalInvalidInRegister}}</div>
                                            <div class="invalid-stat-label">Total -999 Values</div>
                                        </div>
                                        <div class="invalid-stat-item">
                                            <div class="invalid-stat-number">${{totalFusesInRegister}}</div>
                                            <div class="invalid-stat-label">Total Fuses</div>
                                        </div>
                                        <div class="invalid-stat-item">
                                            <div class="invalid-stat-number">${{totalFusesInRegister > 0 ? ((totalInvalidInRegister/totalFusesInRegister)*100).toFixed(1) : 0}}%</div>
                                            <div class="invalid-stat-label">Invalid Rate</div>
                                        </div>
                                    </div>

                                    <div id="${{registerId}}_content" class="expandable-content">
                                        <div class="table-container">
                                            <table class="data-table">
                                                <thead>
                                                    <tr>
                                                        <th>DFF Token ID</th>
                                                        <th>Token Name</th>
                                                        <th>First Socket Upload</th>
                                                        <th>Upload Process Step</th>
                                                        <th>SSID</th>
                                                        <th>Ref Level</th>
                                                        <th>Module</th>
                                                        <th>Fuse Name</th>
                                                        <th>Fuse Register</th>
                                                        <th>Invalid Count (-999)</th>
                                                        <th>Total Fuses</th>
                                                        <th>Visual IDs (Sample)</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                `;

                                invalidTokens.forEach(token => {{
                                    const statusColor = token.status === 'Good' ? '#28a745' : '#dc3545';
                                    html += `
                                        <tr>
                                            <td title="${{token.dff_token_id || ''}}">${{token.dff_token_id || ''}}</td>
                                            <td title="${{token.token_name || ''}}">${{token.token_name || ''}}</td>
                                            <td title="${{token.first_socket_upload || ''}}">${{token.first_socket_upload || ''}}</td>
                                            <td title="${{token.upload_process_step || ''}}">${{token.upload_process_step || ''}}</td>
                                            <td title="${{token.ssid || ''}}">${{token.ssid || ''}}</td>
                                            <td title="${{token.ref_level || ''}}">${{token.ref_level || ''}}</td>
                                            <td title="${{token.module || ''}}">${{token.module || ''}}</td>
                                            <td title="${{token.fuse_name || ''}}">${{token.fuse_name || ''}}</td>
                                            <td title="${{token.fuse_register || ''}}">${{token.fuse_register || ''}}</td>
                                            <td style="color: ${{statusColor}}; font-weight: bold;">${{token.invalid_count || 0}}</td>
                                            <td>${{token.total_fuses || 0}}</td>
                                            <td title="${{token.visual_id || ''}}">${{token.visual_id || ''}}</td>
                                        </tr>
                                    `;
                                }});

                                html += `
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }});

                        html += '</div>';
                    }}

                    contentDiv.innerHTML = html;
                }}

                function loadSspecContent() {{
                    const contentDiv = document.getElementById('sspec-content');
                    if (!statsData.sspec) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No sspec data available</div>';
                        return;
                    }}

                    let totalRegisterSize = 0;
                    if (statsData.sspec.register_statistics) {{
                        Object.values(statsData.sspec.register_statistics).forEach(qdfStats => {{
                            Object.values(qdfStats).forEach(stats => {{
                                if (stats.bit_analysis && stats.bit_analysis.register_size) {{
                                    totalRegisterSize += stats.bit_analysis.register_size;
                                }}
                            }});
                        }});
                    }}

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total Register Size</h3>
                                <div class="stat-value">${{totalRegisterSize || 0}}</div>
                                <div class="stat-description">Total bits across all registers</div>
                                <div class="stat-subdescription">Sum of all register sizes in bits</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🧬</span>Registers</h3>
                                <div class="stat-value">${{statsData.sspec.unique_registers || 0}}</div>
                                <div class="stat-description">Unique registers processed</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">📁</span>Fuse Name</h3>
                                <div class="stat-value">${{statsData.sspec.unique_fuse_names || 0}}</div>
                                <div class="stat-description">Unique fuse names</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🎯</span>QDFs Processed</h3>
                                <div class="stat-value">${{statsData.sspec.qdfs_processed || 0}}</div>
                                <div class="stat-description">Quality data formats</div>
                            </div>
                        </div>
                    `;

                    if (statsData.sspec.register_statistics) {{
                        html += '<div class="chart-container"><h3>📋 Per-Register Analysis</h3>';

                        Object.entries(statsData.sspec.register_statistics).forEach(([registerName, qdfStats]) => {{
                            html += `
                                <div class="section-header" onclick="toggleRegisterExpansion('${{registerName.replace(/[^a-zA-Z0-9]/g, '_')}}')">
                                    <span class="section-title">📌 ${{registerName}}</span>
                                    <div class="section-badge">
                                        <button class="download-btn" onclick="event.stopPropagation(); downloadRegisterAnalysis('${{registerName}}', ${{JSON.stringify(qdfStats).replace(/"/g, '&quot;')}})">
                                            📥 Download CSV
                                        </button>
                                        <span id="${{registerName.replace(/[^a-zA-Z0-9]/g, '_')}}_arrow">▼</span>
                                    </div>
                                </div>
                                <div id="${{registerName.replace(/[^a-zA-Z0-9]/g, '_')}}_content" class="expandable-content">
                                    <div class="table-container">
                                        <table class="register-analysis-table">
                                            <thead>
                                                <tr>
                                                    <th>QDF</th>
                                                    <th>Register Size (bits)</th>
                                                    <th>VF Heap Unused</th>
                                                    <th>Static Bits (0/1)</th>
                                                    <th>Dynamic Bits (m)</th>
                                                    <th>Sort Bits (s)</th>
                                                    <th>Variable Bits (m+s)</th>
                                                    <th>Valid Extractions</th>
                                                    <th>Valid Hex</th>
                                                    <th>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                            `;

                            Object.entries(qdfStats).forEach(([qdf, stats]) => {{
                                const bitAnalysis = stats.bit_analysis;
                                const registerSize = bitAnalysis ? bitAnalysis.register_size : 'N/A';

                                let vfHeapUnused = 'N/A';
                                if (stats.vf_heap_unused_bit_length !== undefined && bitAnalysis && bitAnalysis.register_size > 0) {{
                                    const vfHeapUnusedBits = stats.vf_heap_unused_bit_length;
                                    const vfHeapUnusedPercentage = stats.vf_heap_unused_percentage || 0;
                                    vfHeapUnused = `${{vfHeapUnusedBits}} (${{vfHeapUnusedPercentage}}%)`;
                                }}

                                const staticBits = bitAnalysis ? `${{bitAnalysis.static_bits}} (${{((bitAnalysis.static_bits / bitAnalysis.register_size) * 100).toFixed(1)}}%)` : 'N/A';
                                const dynamicBits = bitAnalysis ? `${{bitAnalysis.dynamic_bits}} (${{((bitAnalysis.dynamic_bits / bitAnalysis.register_size) * 100).toFixed(1)}}%)` : 'N/A';
                                const sortBits = bitAnalysis ? `${{bitAnalysis.sort_bits}} (${{((bitAnalysis.sort_bits / bitAnalysis.register_size) * 100).toFixed(1)}}%)` : 'N/A';
                                const variableBits = bitAnalysis ? `${{bitAnalysis.dynamic_bits + bitAnalysis.sort_bits}} (${{(((bitAnalysis.dynamic_bits + bitAnalysis.sort_bits) / bitAnalysis.register_size) * 100).toFixed(1)}}%)` : 'N/A';

                                html += `
                                    <tr>
                                        <td><strong>${{qdf}}</strong></td>
                                        <td>${{registerSize}}</td>
                                        <td>${{vfHeapUnused}}</td>
                                        <td>${{staticBits}}</td>
                                        <td>${{dynamicBits}}</td>
                                        <td>${{sortBits}}</td>
                                        <td>${{variableBits}}</td>
                                        <td>${{stats.valid_extractions}}/${{stats.fuse_definitions}} (${{stats.valid_extractions_percent}}%)</td>
                                        <td>${{stats.valid_hex}}/${{stats.fuse_definitions}} (${{stats.valid_hex_percent}}%)</td>
                                        <td>
                                            <button class="qdf-download-btn" onclick="downloadQDFSspecData('${{registerName}}', '${{qdf}}')">
                                                📥 ${{qdf}} CSV
                                            </button>
                                        </td>
                                    </tr>
                                `;
                            }});

                            html += `
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            `;
                        }});

                        html += '</div>';
                    }}

                    contentDiv.innerHTML = html;
                }}

                function loadStatusCheckContent() {{
                    const contentDiv = document.getElementById('statuscheck-content');
                    if (!statsData.statuscheck || !statsData.statuscheck.total_fuses) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No StatusCheck data available</div>';
                        return;
                    }}

                    const data = statsData.statuscheck;
                    const percentages = data.statuscheck_percentages || {{}};

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total Fuses Analyzed</h3>
                                <div class="stat-value">${{data.total_fuses || 0}}</div>
                                <div class="stat-description">Fuses in unit-data-xsplit-sspec</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">📋</span>Visual IDs</h3>
                                <div class="stat-value">${{data.visual_ids ? data.visual_ids.length : 0}}</div>
                                <div class="stat-description">Unique units tested</div>
                                <div class="stat-subdescription">${{data.visual_ids ? data.visual_ids.join(', ') : 'N/A'}}</div>
                            </div>
                        </div>

                        <div class="data-section">
                            <h2>📈 StatusCheck Distribution</h2>
                            <div class="stats-grid">
                                <div class="stat-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                                    <h3><span class="icon">✅</span>Static</h3>
                                    <div class="stat-value">${{percentages.static ? percentages.static.count : 0}}</div>
                                    <div class="stat-description">${{percentages.static ? percentages.static.percentage : 0}}% of total</div>
                                    <div class="stat-subdescription">QDF default matches ITF</div>
                                </div>
                                <div class="stat-card" style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);">
                                    <h3><span class="icon">🔄</span>Dynamic</h3>
                                    <div class="stat-value">${{percentages.dynamic ? percentages.dynamic.count : 0}}</div>
                                    <div class="stat-description">${{percentages.dynamic ? percentages.dynamic.percentage : 0}}% of total</div>
                                    <div class="stat-subdescription">DFF value matches ITF</div>
                                </div>
                                <div class="stat-card" style="background: linear-gradient(135deg, #6f42c1 0%, #563d7c 100%);">
                                    <h3><span class="icon">🔐</span>FLE</h3>
                                    <div class="stat-value">${{percentages.FLE ? percentages.FLE.count : 0}}</div>
                                    <div class="stat-description">${{percentages.FLE ? percentages.FLE.percentage : 0}}% of total</div>
                                    <div class="stat-subdescription">Field-level encrypted fuses</div>
                                </div>
                                <div class="stat-card" style="background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);">
                                    <h3><span class="icon">🔧</span>Sort</h3>
                                    <div class="stat-value">${{percentages.sort ? percentages.sort.count : 0}}</div>
                                    <div class="stat-description">${{percentages.sort ? percentages.sort.percentage : 0}}% of total</div>
                                    <div class="stat-subdescription">Sort-skip quality control</div>
                                </div>
                                <div class="stat-card" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);">
                                    <h3><span class="icon">❌</span>Mismatch</h3>
                                    <div class="stat-value">${{percentages['!mismatch!'] ? percentages['!mismatch!'].count : 0}}</div>
                                    <div class="stat-description">${{percentages['!mismatch!'] ? percentages['!mismatch!'].percentage : 0}}% of total</div>
                                    <div class="stat-subdescription">DFF and QDF don't match ITF</div>
                                </div>
                            </div>
                        </div>

                        <div class="data-section">
                            <h2>📊 Per-Unit Breakdown</h2>
                    `;

                    if (data.statuscheck_by_vid) {{
                        Object.entries(data.statuscheck_by_vid).forEach(([vid, counts]) => {{
                            const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
                            html += `
                                <div class="expandable">
                                    <div class="expandable-header" onclick="toggleMismatchExpansion('statuscheck_${{vid}}')">
                                        <span><strong>Visual ID: ${{vid}}</strong></span>
                                        <span>${{total}} fuses <span id="statuscheck_${{vid}}_arrow">▼</span></span>
                                    </div>
                                    <div id="statuscheck_${{vid}}_content" class="expandable-content">
                                        <div class="data-grid">
                            `;

                            Object.entries(counts).forEach(([status, count]) => {{
                                const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                                let color = '#333';
                                if (status === 'static') color = '#28a745';
                                else if (status === 'dynamic') color = '#007bff';
                                else if (status === 'FLE') color = '#6f42c1';
                                else if (status === 'sort') color = '#ffc107';
                                else if (status === '!mismatch!') color = '#dc3545';

                                html += `
                                    <div class="data-item" style="border-left-color: ${{color}};">
                                        <strong>${{status}}</strong>
                                        <span>${{count}} (${{pct}}%)</span>
                                    </div>
                                `;
                            }});

                            html += `
                                        </div>
                                    </div>
                                </div>
                            `;
                        }});
                    }}

                    html += '</div>';
                    contentDiv.innerHTML = html;
                }}

                function loadUnitSummaryContent() {{
                    const contentDiv = document.getElementById('unitsummary-content');
                    if (!statsData.statuscheck || !statsData.statuscheck.per_unit_register_stats) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No per-unit summary data available</div>';
                        return;
                    }}

                    const perUnitStats = statsData.statuscheck.per_unit_register_stats;
                    const visualIds = statsData.statuscheck.visual_ids || [];

                    let html = `
                        <div class="alert alert-info">
                            <h4>📊 Per-Unit StatusCheck Summary by Register</h4>
                            <p>This tab shows detailed StatusCheck breakdown for each visual ID across all registers, sorted by register name.</p>
                            <p><strong>💡 Tip:</strong> In the S_UnitData_by_Fuse CSV file, apply conditional formatting in Excel to highlight cells containing "!mismatch!" in red for easy identification.</p>
                            <p><strong>Excel Formula:</strong> <code>=SEARCH("!mismatch!",cell)>0</code> → Fill with red background</p>
                        </div>
                    `;

                    // High-Level Summary: All Visual IDs Combined
                    html += `
                        <div class="data-section">
                            <h2>🎯 High-Level Summary - All Visual IDs</h2>
                            <div class="table-container">
                                <table class="register-analysis-table">
                                    <thead>
                                        <tr>
                                            <th>Visual ID</th>
                                            <th>Registers</th>
                                            <th>Total Fuses</th>
                                            <th style="background: #28a745;">Static</th>
                                            <th style="background: #007bff;">Dynamic</th>
                                            <th style="background: #6f42c1;">FLE</th>
                                            <th style="background: #ffc107; color: #000;">Sort</th>
                                            <th style="background: #dc3545;">!mismatch!</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;

                    // Calculate summary for each Visual ID
                    visualIds.forEach(vid => {{
                        const vidStats = perUnitStats[vid] || {{}};
                        const registers = Object.keys(vidStats).sort();
                        
                        // Aggregate counts across all registers for this visualID
                        const totalCounts = {{'static': 0, 'dynamic': 0, 'FLE': 0, 'sort': 0, '!mismatch!': 0}};
                        let grandTotal = 0;
                        
                        registers.forEach(register => {{
                            const counts = vidStats[register].counts || {{}};
                            Object.keys(totalCounts).forEach(status => {{
                                totalCounts[status] += counts[status] || 0;
                            }});
                            grandTotal += vidStats[register].total || 0;
                        }});

                        const registerList = registers.join(', ');
                        
                        html += `
                            <tr>
                                <td><strong>${{vid}}</strong></td>
                                <td style="font-size: 0.9em;">${{registerList}}</td>
                                <td><strong>${{grandTotal}}</strong></td>
                                <td>${{totalCounts.static}} <span style="color: #666; font-size: 0.9em;">(${{(100 * totalCounts.static / grandTotal).toFixed(1)}}%)</span></td>
                                <td>${{totalCounts.dynamic}} <span style="color: #666; font-size: 0.9em;">(${{(100 * totalCounts.dynamic / grandTotal).toFixed(1)}}%)</span></td>
                                <td>${{totalCounts.FLE}} <span style="color: #666; font-size: 0.9em;">(${{(100 * totalCounts.FLE / grandTotal).toFixed(1)}}%)</span></td>
                                <td>${{totalCounts.sort}} <span style="color: #666; font-size: 0.9em;">(${{(100 * totalCounts.sort / grandTotal).toFixed(1)}}%)</span></td>
                                <td style="background: ${{totalCounts['!mismatch!'] > 0 ? '#ffe6e6' : 'transparent'}}; font-weight: ${{totalCounts['!mismatch!'] > 0 ? 'bold' : 'normal'}}; color: ${{totalCounts['!mismatch!'] > 0 ? '#dc3545' : 'inherit'}};">
                                    ${{totalCounts['!mismatch!']}} <span style="color: #666; font-size: 0.9em;">(${{(100 * totalCounts['!mismatch!'] / grandTotal).toFixed(1)}}%)</span>
                                </td>
                            </tr>
                        `;
                    }});

                    html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;

                    // Per-Visual ID Detailed Breakdown
                    html += '<div class="data-section"><h2>📋 Detailed Per-Visual ID Breakdown</h2></div>';

                    // Create tabs for each visual ID
                    visualIds.forEach((vid, index) => {{
                        const vidStats = perUnitStats[vid] || {{}};
                        const registers = Object.keys(vidStats).sort();
                        
                        html += `
                            <div class="data-section">
                                <h2>👁️ Visual ID: ${{vid}}</h2>
                                <div class="table-container">
                                    <table class="register-analysis-table">
                                        <thead>
                                            <tr>
                                                <th>Register</th>
                                                <th>Total Fuses</th>
                                                <th style="background: #28a745;">Static</th>
                                                <th style="background: #007bff;">Dynamic</th>
                                                <th style="background: #6f42c1;">FLE</th>
                                                <th style="background: #ffc107; color: #000;">Sort</th>
                                                <th style="background: #dc3545;">!mismatch!</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                        `;

                        registers.forEach(register => {{
                            const regData = vidStats[register];
                            const counts = regData.counts || {{}};
                            const percentages = regData.percentages || {{}};
                            const total = regData.total || 0;

                            const staticCount = counts.static || 0;
                            const dynamicCount = counts.dynamic || 0;
                            const fleCount = counts.FLE || 0;
                            const sortCount = counts.sort || 0;
                            const mismatchCount = counts['!mismatch!'] || 0;

                            const staticPct = percentages.static || 0;
                            const dynamicPct = percentages.dynamic || 0;
                            const flePct = percentages.FLE || 0;
                            const sortPct = percentages.sort || 0;
                            const mismatchPct = percentages['!mismatch!'] || 0;

                            html += `
                                <tr>
                                    <td><strong>${{register}}</strong></td>
                                    <td>${{total}}</td>
                                    <td>${{staticCount}} <span style="color: #666; font-size: 0.9em;">(${{staticPct}}%)</span></td>
                                    <td>${{dynamicCount}} <span style="color: #666; font-size: 0.9em;">(${{dynamicPct}}%)</span></td>
                                    <td>${{fleCount}} <span style="color: #666; font-size: 0.9em;">(${{flePct}}%)</span></td>
                                    <td>${{sortCount}} <span style="color: #666; font-size: 0.9em;">(${{sortPct}}%)</span></td>
                                    <td style="background: ${{mismatchCount > 0 ? '#ffe6e6' : 'transparent'}}; font-weight: ${{mismatchCount > 0 ? 'bold' : 'normal'}}; color: ${{mismatchCount > 0 ? '#dc3545' : 'inherit'}};">
                                        ${{mismatchCount}} <span style="color: #666; font-size: 0.9em;">(${{mismatchPct}}%)</span>
                                    </td>
                                </tr>
                            `;
                        }});

                        // Add totals row
                        const allCounts = {{'static': 0, 'dynamic': 0, 'FLE': 0, 'sort': 0, '!mismatch!': 0}};
                        let grandTotal = 0;
                        registers.forEach(register => {{
                            const counts = vidStats[register].counts || {{}};
                            Object.keys(allCounts).forEach(status => {{
                                allCounts[status] += counts[status] || 0;
                            }});
                            grandTotal += vidStats[register].total || 0;
                        }});

                        html += `
                            <tr style="background: #f8f9fa; font-weight: 600;">
                                <td><strong>TOTAL</strong></td>
                                <td><strong>${{grandTotal}}</strong></td>
                                <td><strong>${{allCounts.static}}</strong> <span style="color: #666; font-size: 0.9em; font-weight: normal;">(${{(100 * allCounts.static / grandTotal).toFixed(1)}}%)</span></td>
                                <td><strong>${{allCounts.dynamic}}</strong> <span style="color: #666; font-size: 0.9em; font-weight: normal;">(${{(100 * allCounts.dynamic / grandTotal).toFixed(1)}}%)</span></td>
                                <td><strong>${{allCounts.FLE}}</strong> <span style="color: #666; font-size: 0.9em; font-weight: normal;">(${{(100 * allCounts.FLE / grandTotal).toFixed(1)}}%)</span></td>
                                <td><strong>${{allCounts.sort}}</strong> <span style="color: #666; font-size: 0.9em; font-weight: normal;">(${{(100 * allCounts.sort / grandTotal).toFixed(1)}}%)</span></td>
                                <td style="background: ${{allCounts['!mismatch!'] > 0 ? '#ffcccc' : 'transparent'}};">
                                    <strong style="color: ${{allCounts['!mismatch!'] > 0 ? '#dc3545' : 'inherit'}};">${{allCounts['!mismatch!']}}</strong> 
                                    <span style="color: #666; font-size: 0.9em; font-weight: normal;">(${{(100 * allCounts['!mismatch!'] / grandTotal).toFixed(1)}}%)</span>
                                </td>
                            </tr>
                        `;

                        html += `
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        `;
                    }});

                    contentDiv.innerHTML = html;
                }}

                function loadITFContent() {{
                    const contentDiv = document.getElementById('itf-content');
                    if (!statsData.itf) {{
                        contentDiv.innerHTML = '<div class="alert alert-info">No ITF data available</div>';
                        return;
                    }}

                    let html = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3><span class="icon">📊</span>Total ITF Files</h3>
                                <div class="stat-value">${{statsData.itf.total_files || 0}}</div>
                                <div class="stat-description">ITF files processed</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">👁️</span>Visual IDs</h3>
                                <div class="stat-value">${{statsData.itf.unique_visual_ids || 0}}</div>
                                <div class="stat-description">Unique visual identifiers</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🎯</span>TNAME Rows</h3>
                                <div class="stat-value">${{statsData.itf.total_tname_rows || 0}}</div>
                                <div class="stat-description">Individual TNAME-VALUE rows</div>
                            </div>
                            <div class="stat-card">
                                <h3><span class="icon">🔗</span>Fullstring Rows</h3>
                                <div class="stat-value">${{statsData.itf.total_fullstring_rows || 0}}</div>
                                <div class="stat-description">Combined fullstring rows</div>
                            </div>
                        </div>
                    `;

                    if (statsData.itf.ssid_breakdown) {{
                        html += createBreakdownSection('ssid_breakdown', 'Breakdown by SSID', statsData.itf.ssid_breakdown);
                    }}

                    contentDiv.innerHTML = html;
                }}

                function createBreakdownSection(id, title, data) {{
                    let html = `<div class="chart-container"><h3>📋 ${{title}}</h3>`;

                    const total = Object.values(data).reduce((sum, count) => sum + count, 0);

                    Object.entries(data).forEach(([key, count]) => {{
                        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                        html += `
                            <div style="margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                                    <span style="font-weight: 600;">${{key}}</span>
                                    <span class="badge badge-info">${{count}} (${{percentage}}%)</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${{percentage}}%;">
                                        ${{percentage}}%
                                    </div>
                                </div>
                            </div>
                        `;
                    }});

                    html += '</div>';
                    return html;
                }}

                function createDetailedCategorizedSection(id, title, categoryData, tokenDetails) {{
                    let html = `<div style="margin-bottom: 30px;"><h4>📋 ${{title}}</h4>`;

                    Object.entries(categoryData).forEach(([category, count]) => {{
                        const tokens = tokenDetails[category] || [];
                        const sectionId = `${{id}}_${{category.replace(/[^a-zA-Z0-9]/g, '_')}}`;

                        html += `
                            <div class="section-header" onclick="toggleDetailedCategoryExpansion('${{sectionId}}')">
                                <span class="section-title">${{category || 'N/A'}}</span>
                                <div class="section-badge">
                                    <span class="badge badge-info">${{count}} tokens</span>
                                    <button class="download-btn" onclick="event.stopPropagation(); downloadCategoryData('${{category}}', '${{title}}', ${{JSON.stringify(tokens).replace(/"/g, '&quot;')}})">
                                        📥 Download CSV
                                    </button>
                                    <span id="${{sectionId}}_arrow">▼</span>
                                </div>
                            </div>
                            <div id="${{sectionId}}_content" class="expandable-content">
                                <div class="table-container">
                                    <table class="data-table">
                                        <thead>
                                            <tr>
                                                <th>DFF Token ID</th>
                                                <th>Token Name</th>
                                                <th>First Socket Upload</th>
                                                <th>Upload Process Step</th>
                                                <th>SSID</th>
                                                <th>Ref Level</th>
                                                <th>Module</th>
                                                <th>Field Name</th>
                                                <th>Field Seq</th>
                                                <th>Fuse Name Ori</th>
                                                <th>Fuse Name</th>
                                                <th>Fuse Register Ori</th>
                                                <th>Fuse Register</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                        `;

                        tokens.forEach(token => {{
                            html += `
                                <tr>
                                    <td title="${{token.dff_token_id_MTL || ''}}">${{token.dff_token_id_MTL || ''}}</td>
                                    <td title="${{token.token_name_MTL || ''}}">${{token.token_name_MTL || ''}}</td>
                                    <td title="${{token.first_socket_upload_MTL || ''}}">${{token.first_socket_upload_MTL || ''}}</td>
                                    <td title="${{token.upload_process_step_MTL || ''}}">${{token.upload_process_step_MTL || ''}}</td>
                                    <td title="${{token.ssid_MTL || ''}}">${{token.ssid_MTL || ''}}</td>
                                    <td title="${{token.ref_level_MTL || ''}}">${{token.ref_level_MTL || ''}}</td>
                                    <td title="${{token.module_MTL || ''}}">${{token.module_MTL || ''}}</td>
                                    <td title="${{token.field_name_MTL || ''}}">${{token.field_name_MTL || ''}}</td>
                                    <td title="${{token.field_name_seq_MTL || ''}}">${{token.field_name_seq_MTL || ''}}</td>
                                    <td title="${{token.fuse_name_ori_MTL || ''}}">${{token.fuse_name_ori_MTL || ''}}</td>
                                    <td title="${{token.fuse_name_MTL || ''}}">${{token.fuse_name_MTL || ''}}</td>
                                    <td title="${{token.fuse_register_ori_MTL || ''}}">${{token.fuse_register_ori_MTL || ''}}</td>
                                    <td title="${{token.fuse_register_MTL || ''}}">${{token.fuse_register_MTL || ''}}</td>
                                </tr>
                            `;
                        }});

                        html += `
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        `;
                    }});

                    html += '</div>';
                    return html;
                }}

                function createMismatchTableSection(id, title, mismatches) {{
                    let html = `
                        <div class="section-header" onclick="toggleMismatchExpansion('${{id}}')">
                            <span class="section-title" style="color: #e53e3e;">⚠️ ${{title}}</span>
                            <div class="section-badge">
                                <span class="badge badge-danger">${{mismatches.length}} items</span>
                                <button class="download-btn" onclick="event.stopPropagation(); downloadMismatchData('${{title}}', ${{JSON.stringify(mismatches).replace(/"/g, '&quot;')}})">
                                    📥 Download CSV
                                </button>
                                <span id="${{id}}_arrow">▼</span>
                            </div>
                        </div>
                        <div id="${{id}}_content" class="expandable-content">
                            <div class="table-container">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>Token Name</th>
                                            <th>Field Name</th>
                                            <th>Module</th>
                                            <th>Fuse Register</th>
                                            <th>Fuse Name</th>
                                            <th>First Socket Upload</th>
                                            <th>SSID</th>
                                            <th>Ref Level</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;

                    mismatches.slice(0, 100).forEach(mismatch => {{
                        html += `
                            <tr>
                                <td title="${{mismatch.token_name_MTL || ''}}">${{mismatch.token_name_MTL || ''}}</td>
                                <td title="${{mismatch.field_name_MTL || ''}}">${{mismatch.field_name_MTL || ''}}</td>
                                <td title="${{mismatch.module_MTL || ''}}">${{mismatch.module_MTL || ''}}</td>
                                <td title="${{mismatch.fuse_register_MTL || ''}}">${{mismatch.fuse_register_MTL || ''}}</td>
                                <td title="${{mismatch.fuse_name_MTL || ''}}">${{mismatch.fuse_name_MTL || ''}}</td>
                                <td title="${{mismatch.first_socket_upload_MTL || ''}}">${{mismatch.first_socket_upload_MTL || ''}}</td>
                                <td title="${{mismatch.ssid_MTL || ''}}">${{mismatch.ssid_MTL || ''}}</td>
                                <td title="${{mismatch.ref_level_MTL || ''}}">${{mismatch.ref_level_MTL || ''}}</td>
                            </tr>
                        `;
                    }});

                    if (mismatches.length > 100) {{
                        html += `
                            <tr>
                                <td colspan="8" style="text-align: center; font-style: italic; color: #555; font-size: 14px; padding: 20px;">
                                    Showing first 100 of ${{mismatches.length}} mismatches. Download CSV for complete data.
                                </td>
                            </tr>
                        `;
                    }}

                    html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;

                    return html;
                }}

                // Download functions
                function downloadCategoryData(category, title, tokens) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const ws = XLSX.utils.json_to_sheet(tokens);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Tokens");
                    XLSX.writeFile(wb, `MTL_OLF_${{title.replace(/[^a-zA-Z0-9]/g, '_')}}_${{category.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadMismatchData(title, mismatches) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const ws = XLSX.utils.json_to_sheet(mismatches);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Mismatches");
                    XLSX.writeFile(wb, `Matching_${{title.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadRegisterMismatchData(register, mismatchTokens) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const ws = XLSX.utils.json_to_sheet(mismatchTokens);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Register Mismatches");
                    XLSX.writeFile(wb, `Register_Mismatches_${{register.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadMissingTokensData(register, missingTokens) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const ws = XLSX.utils.json_to_sheet(missingTokens);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Missing Tokens");
                    XLSX.writeFile(wb, `DFF_Missing_Tokens_${{register.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadInvalidTokensData(register, invalidTokens) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const ws = XLSX.utils.json_to_sheet(invalidTokens);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Invalid Tokens");
                    XLSX.writeFile(wb, `DFF_Invalid_Tokens_${{register.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadRegisterAnalysis(registerName, qdfStats) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const analysisData = [];
                    Object.entries(qdfStats).forEach(([qdf, stats]) => {{
                        const bitAnalysis = stats.bit_analysis;

                        let vfHeapUnusedBits = 'N/A';
                        let vfHeapUnusedPercent = 'N/A';
                        if (stats.vf_heap_unused_bit_length !== undefined) {{
                            vfHeapUnusedBits = stats.vf_heap_unused_bit_length;
                            vfHeapUnusedPercent = stats.vf_heap_unused_percentage || 0;
                        }}

                        analysisData.push({{
                            QDF: qdf,
                            RegisterSize: bitAnalysis ? bitAnalysis.register_size : 'N/A',
                            VFHeapUnusedBits: vfHeapUnusedBits,
                            VFHeapUnusedPercent: vfHeapUnusedPercent,
                            StaticBits: bitAnalysis ? bitAnalysis.static_bits : 'N/A',
                            StaticBitsPercent: bitAnalysis ? ((bitAnalysis.static_bits / bitAnalysis.register_size) * 100).toFixed(1) : 'N/A',
                            DynamicBits: bitAnalysis ? bitAnalysis.dynamic_bits : 'N/A',
                            DynamicBitsPercent: bitAnalysis ? ((bitAnalysis.dynamic_bits / bitAnalysis.register_size) * 100).toFixed(1) : 'N/A',
                            SortBits: bitAnalysis ? bitAnalysis.sort_bits : 'N/A',
                            SortBitsPercent: bitAnalysis ? ((bitAnalysis.sort_bits / bitAnalysis.register_size) * 100).toFixed(1) : 'N/A',
                            VariableBits: bitAnalysis ? bitAnalysis.dynamic_bits + bitAnalysis.sort_bits : 'N/A',
                            VariableBitsPercent: bitAnalysis ? (((bitAnalysis.dynamic_bits + bitAnalysis.sort_bits) / bitAnalysis.register_size) * 100).toFixed(1) : 'N/A',
                            ValidExtractions: stats.valid_extractions,
                            TotalFuseDefinitions: stats.fuse_definitions,
                            ValidExtractionsPercent: stats.valid_extractions_percent,
                            ValidHex: stats.valid_hex,
                            ValidHexPercent: stats.valid_hex_percent
                        }});
                    }});

                    const ws = XLSX.utils.json_to_sheet(analysisData);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Analysis");
                    XLSX.writeFile(wb, `sspec_Register_Analysis_${{registerName.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function downloadQDFSspecData(registerName, qdf) {{
                    if (typeof XLSX === 'undefined') {{
                        alert('Excel export library not loaded. Please check your internet connection.');
                        return;
                    }}
                    const qdfData = breakdownData.filter(row => 
                        row.RegisterName === registerName && 
                        (row[`${{qdf}}_binaryValue`] !== undefined || row[`${{qdf}}_hexValue`] !== undefined)
                    );

                    if (qdfData.length === 0) {{
                        alert(`No data found for register "${{registerName}}" and QDF "${{qdf}}"`);
                        return;
                    }}

                    const sspecData = qdfData.map(row => ({{
                        RegisterName: row.RegisterName || '',
                        RegisterName_fuseDef: row.RegisterName_fuseDef || '',
                        FuseGroup_Name_fuseDef: row.FuseGroup_Name_fuseDef || '',
                        Fuse_Name_fuseDef: row.Fuse_Name_fuseDef || '',
                        StartAddress_fuseDef: row.StartAddress_fuseDef || '',
                        EndAddress_fuseDef: row.EndAddress_fuseDef || '',
                        bit_length: row.bit_length || 0,
                        [`${{qdf}}_binaryValue`]: row[`${{qdf}}_binaryValue`] || '',
                        [`${{qdf}}_hexValue`]: row[`${{qdf}}_hexValue`] || ''
                    }}));

                    const ws = XLSX.utils.json_to_sheet(sspecData);
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "sspec Data");
                    XLSX.writeFile(wb, `xsplit-sspec_${{qdf}}_${{registerName.replace(/[^a-zA-Z0-9]/g, '_')}}.xlsx`);
                }}

                function toggleDetailedCategoryExpansion(id) {{
                    const content = document.getElementById(id + '_content');
                    const arrow = document.getElementById(id + '_arrow');

                    if (content && arrow) {{
                        if (content.classList.contains('show')) {{
                            content.classList.remove('show');
                            arrow.textContent = '▼';
                        }} else {{
                            content.classList.add('show');
                            arrow.textContent = '▲';
                        }}
                    }}
                }}

                function toggleMismatchExpansion(id) {{
                    const content = document.getElementById(id + '_content');
                    const arrow = document.getElementById(id + '_arrow');

                    if (content && arrow) {{
                        if (content.classList.contains('show')) {{
                            content.classList.remove('show');
                            arrow.textContent = '▼';
                        }} else {{
                            content.classList.add('show');
                            arrow.textContent = '▲';
                        }}
                    }}
                }}

                function toggleRegisterExpansion(id) {{
                    const content = document.getElementById(id + '_content');
                    const arrow = document.getElementById(id + '_arrow');

                    if (content && arrow) {{
                        if (content.classList.contains('show')) {{
                            content.classList.remove('show');
                            arrow.textContent = '▼';
                        }} else {{
                            content.classList.add('show');
                            arrow.textContent = '▲';
                        }}
                    }}
                }}

                document.addEventListener('DOMContentLoaded', function() {{
                    loadOverviewContent();
                }});


    </script>
</body>
</html>"""
