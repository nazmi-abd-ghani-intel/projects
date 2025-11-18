# Unit Data SSPEC Feature

## Overview
The Unit Data SSPEC feature maps individual unit fuse data from ITF files to the SSPEC breakdown structure. It creates CSV files that extend the xsplit-sspec format with per-unit columns showing how each unit's actual fuse values compare to the reference QDF values.

## File Format

### Input Files
1. **xsplit-sspec CSV**: Reference SSPEC breakdown file
   - Contains: RegisterName, Fuse_Name, StartAddress, EndAddress, bit_length, {QDF}_binaryValue, {QDF}_hexValue

2. **ITF Fullstring CSV**: Unit-level fuse data
   - Contains: visualid, Register, TNAME_VALUE (in RLE or binary format)
   - TNAME_VALUE examples:
     - Binary: `0101010101`
     - RLE: `A32B6A8B2AB2A4BABA` (A=zeros, B=ones)

### Output File
**Filename**: `unit-data-xsplit-sspec_{QDF}_{fusefilename}.csv`

**Structure**: Original xsplit-sspec columns + per-unit columns
- Original columns: RegisterName, FuseGroup_Name_fuseDef, Fuse_Name_fuseDef, StartAddress_fuseDef, EndAddress_fuseDef, bit_length, {QDF}_binaryValue, {QDF}_hexValue
- Per-unit columns (for each visualID):
  - `{visualID}_binaryValue`: Binary value extracted from unit's fuse string
  - `{visualID}_hexValue`: Hex representation of the binary value

**Example**:
```csv
RegisterName,Fuse_Name_fuseDef,StartAddress,EndAddress,bit_length,L2FW_binaryValue,L2FW_hexValue,U538G05900350_binaryValue,U538G05900350_hexValue,U538G05900503_binaryValue,U538G05900503_hexValue
CPU0,SOCFuseGen_reserved_HeapPointer_row_0_bit_0,0,15,16,b0000010111110000,0X5F0,b1100000111110000,0XC1F0,b1100000111110000,0XC1F0
```

## RLE Decoding

### Format
RLE (Running Length Encoder) uses A and B characters followed by digit counts:
- `A` + digits = that many zeros (A without digits = 1 zero)
- `B` + digits = that many ones (B without digits = 1 one)

### Examples
- `A5` = `00000` (5 zeros)
- `B3` = `111` (3 ones)
- `A` = `0` (1 zero)
- `B` = `1` (1 one)
- `A5BA2B3` = `00000100111` (5 zeros, 1 one, 2 zeros, 3 ones)

### Implementation
```python
def decode_rle(rle_string: str) -> str:
    """
    Decode RLE format to binary string.
    A5BA2B3 = 00000100111
    """
    binary = []
    i = 0
    while i < len(rle_string):
        char = rle_string[i]
        if char.upper() == 'A':  # zeros
            i += 1
            num_str = ''
            while i < len(rle_string) and rle_string[i].isdigit():
                num_str += rle_string[i]
                i += 1
            count = int(num_str) if num_str else 1
            binary.append('0' * count)
        elif char.upper() == 'B':  # ones
            i += 1
            num_str = ''
            while i < len(rle_string) and rle_string[i].isdigit():
                num_str += rle_string[i]
                i += 1
            count = int(num_str) if num_str else 1
            binary.append('1' * count)
        else:
            i += 1
    return ''.join(binary)
```

## Bit Extraction

### LSB Addressing
Bits are extracted using LSB (Least Significant Bit) addressing, matching the existing SSPEC breakdown logic:

```python
def extract_fuse_bits(fuse_binary: str, start_addr: int, end_addr: int) -> str:
    """
    Extract bits from fuse string using LSB addressing.
    
    Args:
        fuse_binary: Full binary fuse string
        start_addr: Start bit address (LSB)
        end_addr: End bit address (LSB, inclusive)
    
    Returns:
        Extracted binary substring
    """
    fuse_length = len(fuse_binary)
    if start_addr > end_addr or end_addr >= fuse_length:
        return ''
    
    # Convert LSB address to array index
    start_idx = fuse_length - 1 - end_addr
    end_idx = fuse_length - 1 - start_addr + 1
    
    return fuse_binary[start_idx:end_idx]
```

### Example
For a 16-bit fuse string `1100000111110000`:
- Bit positions (LSB): 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0
- Extracting bits 0-7 (StartAddress=0, EndAddress=7):
  - start_idx = 16 - 1 - 7 = 8
  - end_idx = 16 - 1 - 0 + 1 = 16
  - Result: `11110000` (bits 8-15 in the string)

## Integration

### Pipeline Flow
1. **UBE Processing**: Extract lotname and location from UBE filename
2. **ITF Processing**: Generate ITF fullstring CSV with RLE-encoded data
3. **SSPEC Processing**: Generate xsplit-sspec CSV for each QDF
4. **Unit Data SSPEC**: Map ITF unit data to SSPEC breakdown
   - Calls: `FFRProcessor.create_unit_data_sspec_csv(itf_processed)`
   - For each QDF in target_qdf_set:
     - Find xsplit-sspec CSV
     - Load ITF fullstring data
     - Map each Fuse_Name to unit values
     - Write unit-data-xsplit-sspec CSV

### Code Location
- Processor: `src/processors/unit_data_sspec.py` (UnitDataSspecProcessor)
- Integration: `src/ffr_processor.py` (FFRProcessor.create_unit_data_sspec_csv)
- Main entry: `src/main.py` (after sspec breakdown creation)

## Requirements
- ITF files must be processed (`-ituff` argument)
- UBE file must be processed to extract lotname/location (`-ube` argument)
- SSPEC file must be processed to generate xsplit-sspec (`-sspec` argument)
- ITF fullstring file naming: `itf_tname_value_rows_fullstring_{fusefilename}_{lotname}_{location}.csv`

## Usage

### Command Line
```powershell
python -m src.main input_files output `
  -sspec L2FW `
  -ube input_files/P5420950_6197.ube `
  -ituff input_files/P5420950_6197
```

### Output
- Generated files: `output/unit-data-xsplit-sspec_L2FW_{fusefilename}.csv`
- File size: ~3.5 MB for 21,000 rows with 2 units
- Columns: Original (9) + per-unit (2 × number of units)

## Statistics
From test run with P5420950_6197 data:
- Units processed: 2 (U538G05900350, U538G05900503)
- Total rows: 21,084 fuse definitions
- Registers: CPU0, GCD, PCD
- File size: 3,488,664 bytes

## Error Handling
- Missing ITF file: Warning message, returns False
- Missing xsplit-sspec: Skips that QDF
- No unit data for register: Returns empty string values
- Invalid RLE format: Skips unrecognized characters
- Binary already in TNAME_VALUE: Passes through without decoding
