"""XML Parser for MTL_OLF.xml files"""

from typing import List, Dict, Any
from pathlib import Path
import xml.etree.ElementTree as etree


class XMLParser:
    """
    Parses MTL_OLF.xml files and extracts token information.
    """
    
    def __init__(self, sanitizer):
        """
        Initialize the XML parser.
        
        Args:
            sanitizer: CSVSanitizer instance for data cleaning
        """
        self.sanitizer = sanitizer
    
    def parse_xml_optimized(self, xml_file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse XML file with memory optimization using iterparse.
        
        Args:
            xml_file_path: Path to the XML file
            
        Returns:
            List of dictionaries containing parsed data
        """
        try:
            print(f"Successfully parsing: {xml_file_path}")
            print("-" * 60)
            
            # Parse the tree to get root element and total token count
            tree = etree.parse(str(xml_file_path))
            root = tree.getroot()
            
            print(f"Root element: {root.tag}")
            
            tokens = root.findall('.//Token')
            print(f"Found {len(tokens)} Token(s)")
            
            csv_data = []
            
            for token_idx, element in enumerate(tokens):
                if token_idx % 1000 == 0 and token_idx > 0:
                    print(f"  Processed {token_idx} tokens...")
                
                # Extract token-level information from child elements
                dff_token_id = element.findtext('dff_token_id', '')
                token_name = element.findtext('name', '')
                first_socket_upload = element.findtext('first_socket_upload', '')
                upload_process_step = element.findtext('upload_process_step', '')
                ssid = element.findtext('ssid', '')
                ref_level = element.findtext('ref_level', '')
                module = element.findtext('module', '')
                global_type = element.findtext('global_type', '')
                
                # Find all ValueDecoderField elements within ValueDecoder
                value_decoder = element.find('ValueDecoder')
                if value_decoder is not None:
                    fields = value_decoder.findall('ValueDecoderField')
                    
                    if fields:
                        for idx, field in enumerate(fields, 1):
                            field_name = field.findtext('name', '')
                            fuse_name_original = field.findtext('fuse_name', '')
                            fuse_register_original = field.findtext('fuse_register', '')
                            
                            paired_data = self._pair_fuse_names_registers(fuse_name_original, fuse_register_original)
                            
                            for pair in paired_data:
                                row_data = {
                                    'dff_token_id': dff_token_id,
                                    'token_name': token_name,
                                    'first_socket_upload': first_socket_upload,
                                    'upload_process_step': upload_process_step,
                                    'ssid': ssid,
                                    'ref_level': ref_level,
                                    'module': module,
                                    'field_name': field_name,
                                    'field_name_seq': idx,
                                    'fuse_name_ori': fuse_name_original,
                                    'fuse_name': pair['fuse_name'],
                                    'fuse_register_ori': fuse_register_original,
                                    'fuse_register': pair['fuse_register'],
                                    'global_type': global_type
                                }
                                csv_data.append(row_data)
                    else:
                        # No fields found
                        row_data = {
                            'dff_token_id': dff_token_id,
                            'token_name': token_name,
                            'first_socket_upload': first_socket_upload,
                            'upload_process_step': upload_process_step,
                            'ssid': ssid,
                            'ref_level': ref_level,
                            'module': module,
                            'field_name': '',
                            'field_name_seq': 0,
                            'fuse_name_ori': '',
                            'fuse_name': '',
                            'fuse_register_ori': '',
                            'fuse_register': '',
                            'global_type': global_type
                        }
                        csv_data.append(row_data)
            
            print(f"\n✅ XML parsing completed: {len(csv_data)} records extracted")
            return csv_data
            
        except etree.ParseError as e:
            print(f"XML Parse Error: {e}")
            return []
        except FileNotFoundError:
            print(f"Error: File '{xml_file_path}' not found")
            return []
        except Exception as e:
            print(f"Unexpected error parsing XML: {e}")
            return []
    
    def _pair_fuse_names_registers(self, fuse_name_original: str, fuse_register_original: str) -> List[Dict[str, str]]:
        """
        Pair fuse names with registers, handling comma-separated values.
        
        Args:
            fuse_name_original: Original fuse name string (may contain commas)
            fuse_register_original: Original fuse register string (may contain commas)
            
        Returns:
            List of paired fuse name/register dictionaries
        """
        fuse_names = [name.strip() for name in fuse_name_original.split(',') if name.strip()] if fuse_name_original else ['']
        fuse_registers = [reg.strip() for reg in fuse_register_original.split(',') if reg.strip()] if fuse_register_original else ['']
        
        len_names, len_regs = len(fuse_names), len(fuse_registers)
        
        if len_names == len_regs and len_names > 1:
            paired_data = [{'fuse_name': name, 'fuse_register': reg} for name, reg in zip(fuse_names, fuse_registers)]
        elif len_names > 1 and len_regs == 1:
            paired_data = [{'fuse_name': name, 'fuse_register': fuse_registers[0]} for name in fuse_names]
        elif len_names == 1 and len_regs > 1:
            paired_data = [{'fuse_name': fuse_names[0], 'fuse_register': reg} for reg in fuse_registers]
        elif len_names > 1 and len_regs > 1 and len_names != len_regs:
            min_count = min(len_names, len_regs)
            paired_data = [{'fuse_name': fuse_names[i], 'fuse_register': fuse_registers[i]} for i in range(min_count)]
            
            if len_names > min_count:
                last_register = fuse_registers[-1]
                for i in range(min_count, len_names):
                    paired_data.append({'fuse_name': fuse_names[i], 'fuse_register': last_register})
            elif len_regs > min_count:
                last_name = fuse_names[-1]
                for i in range(min_count, len_regs):
                    paired_data.append({'fuse_name': last_name, 'fuse_register': fuse_registers[i]})
        else:
            paired_data = [{'fuse_name': fuse_names[0] if fuse_names else '', 'fuse_register': fuse_registers[0] if fuse_registers else ''}]
        
        return paired_data
