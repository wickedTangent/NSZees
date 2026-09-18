"""PFS0 container structure validation for NSP files.

This module performs instant structural validation of NSP files by checking:
- PFS0 magic bytes
- Header integrity
- File table structure

Does NOT verify cryptographic signatures or content — use nsz --verify for that.
"""

import struct
from pathlib import Path
from typing import Tuple


def check_pfs0_container(filepath: str) -> Tuple[bool, str | None]:
    """Validate PFS0 container structure of an NSP file.
    
    Performs fast structural checks:
    - File exists and is readable
    - PFS0 magic header ("PFS0")
    - Valid file count and string table size
    - Header size matches expectations
    
    Args:
        filepath: Path to the NSP file to validate
        
    Returns:
        (is_valid, error_message)
        - is_valid: True if container structure is valid
        - error_message: None if valid, descriptive error string if invalid
        
    Example:
        >>> is_valid, error = check_pfs0_container("game.nsp")
        >>> if not is_valid:
        ...     print(f"Container check failed: {error}")
    """
    path = Path(filepath)
    
    # Existence check
    if not path.exists():
        return False, f"File not found: {filepath}"
    
    if not path.is_file():
        return False, f"Not a file: {filepath}"
    
    # Size check
    try:
        size = path.stat().st_size
    except OSError as e:
        return False, f"Cannot stat file: {e}"
    
    if size < 16:
        return False, f"File too small ({size} bytes) to be valid PFS0"
    
    # Read and validate header
    try:
        with open(path, 'rb') as f:
            # PFS0 header structure (first 16 bytes):
            # 0x00: magic (4 bytes) - "PFS0"
            # 0x04: file_count (4 bytes, LE uint32)
            # 0x08: string_table_size (4 bytes, LE uint32)
            # 0x0C: reserved (4 bytes)
            header = f.read(16)
            
            if len(header) < 16:
                return False, "Failed to read full PFS0 header"
            
            magic = header[0:4]
            if magic != b'PFS0':
                magic_hex = magic.hex() if len(magic) == 4 else "truncated"
                return False, f"Invalid PFS0 magic: expected 'PFS0', got {magic_hex}"
            
            file_count = struct.unpack('<I', header[4:8])[0]
            string_table_size = struct.unpack('<I', header[8:12])[0]
            
            # Sanity checks
            if file_count == 0:
                return False, "PFS0 file count is zero"
            
            if file_count > 10000:
                return False, f"Suspicious file count: {file_count} (likely corrupted)"
            
            if string_table_size > 10 * 1024 * 1024:  # 10MB string table sanity limit
                return False, f"String table too large: {string_table_size} bytes"
            
            # Calculate expected header size
            # Header: 16 bytes
            # File entries: file_count * 24 bytes each
            # String table: string_table_size bytes
            expected_header_end = 16 + (file_count * 24) + string_table_size
            
            if expected_header_end > size:
                return False, f"Header size ({expected_header_end}) exceeds file size ({size})"
            
    except OSError as e:
        return False, f"I/O error reading file: {e}"
    except Exception as e:
        return False, f"Unexpected error during validation: {e}"
    
    return True, None
