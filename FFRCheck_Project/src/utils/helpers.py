"""Helper functions for FFR processing"""

from typing import Optional, Dict, List, Any


def binary_to_hex_fast(binary_string: str) -> str:
    """
    Convert a binary string to hexadecimal.
    
    Args:
        binary_string: Binary string to convert
        
    Returns:
        Hexadecimal string or 'Q' if conversion fails
    """
    if not binary_string or binary_string == 'N/A':
        return 'Q'

    try:
        binary_clean = binary_string.strip()
        if not binary_clean or not all(bit in '01' for bit in binary_clean):
            return 'Q'

        return hex(int(binary_clean, 2)).upper()

    except (ValueError, TypeError):
        return 'Q'


def breakdown_fuse_string_fast(fuse_string: str, start_addr: str, end_addr: str) -> str:
    """
    Extract specific bits from a fuse string based on start and end addresses.
    
    Args:
        fuse_string: The complete fuse string
        start_addr: Comma-separated start addresses
        end_addr: Comma-separated end addresses
        
    Returns:
        Extracted bits as a string
    """
    if not fuse_string or not start_addr or not end_addr:
        return ''

    try:
        start_addresses = [int(addr) for addr in start_addr.split(',')]
        end_addresses = [int(addr) for addr in end_addr.split(',')]

        fuse_length = len(fuse_string)
        extracted_bits = []

        for start, end in zip(start_addresses, end_addresses):
            if start > end:
                start, end = end, start

            lsb_start = max(0, fuse_length - 1 - end)
            lsb_end = min(fuse_length - 1, fuse_length - 1 - start)

            if lsb_start <= lsb_end:
                extracted_bits.append(fuse_string[lsb_start:lsb_end + 1])

        return ''.join(extracted_bits)

    except (ValueError, IndexError):
        return ''


def analyze_fuse_string_bits(fuse_string: str) -> Optional[Dict[str, int]]:
    """
    Analyze a fuse string to count different types of bits.
    
    Args:
        fuse_string: The fuse string to analyze
        
    Returns:
        Dictionary with bit counts or None if empty
    """
    if not fuse_string:
        return None

    register_size = len(fuse_string)
    static_bits = sum(1 for bit in fuse_string if bit in ['0', '1'])
    dynamic_bits = sum(1 for bit in fuse_string if bit.lower() == 'm')
    sort_bits = sum(1 for bit in fuse_string if bit.lower() == 's')

    return {
        'register_size': register_size,
        'static_bits': static_bits,
        'dynamic_bits': dynamic_bits,
        'sort_bits': sort_bits
    }


def get_register_fuse_string(register_name: str, qdf: str, sspec_data: List[Dict[str, Any]]) -> Optional[str]:
    """
    Get the fuse string for a specific register and QDF from sspec data.
    
    Args:
        register_name: Name of the register
        qdf: QDF identifier
        sspec_data: List of sspec data entries
        
    Returns:
        Fuse string or None if not found
    """
    for sspec_entry in sspec_data:
        if sspec_entry['RegisterName'] == register_name and sspec_entry['QDF'] == qdf:
            return sspec_entry['fuse_string']
    return None
