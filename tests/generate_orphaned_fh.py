#!/usr/bin/env python3
"""
Create a ZIP file with different orphaned entry scenarios for testing ExtendedZipFile.
Orphaned CDH entries are embedded in the EOCD comment field.
"""

import struct
import binascii

def create_complex_orphaned_zip():
    """Create a ZIP with normal, orphaned LFH, and orphaned LFH+CDH pairs."""
    def create_lfh(filename, content, compression=0):
        """Create a Local File Header."""
        filename_bytes = filename.encode('utf-8')
        content_bytes = content.encode('utf-8')
        
        lfh = struct.pack('<4s',    b'PK\x03\x04')
        lfh += struct.pack('<H',    20)
        lfh += struct.pack('<H',    0)
        lfh += struct.pack('<H',    compression)
        lfh += struct.pack('<H',    0)
        lfh += struct.pack('<H',    0)
        lfh += struct.pack('<L',    binascii.crc32(content_bytes) & 0xffffffff)
        lfh += struct.pack('<L',    len(content_bytes))
        lfh += struct.pack('<L',    len(content_bytes))
        lfh += struct.pack('<H',    len(filename_bytes))
        lfh += struct.pack('<H',    0)
        lfh += filename_bytes
        lfh += content_bytes
        
        return lfh

    def create_cdh(filename, content, lfh_offset, compression=0):
        """Create a Central Directory Header."""
        filename_bytes = filename.encode('utf-8')
        content_bytes = content.encode('utf-8')
        
        cdh = struct.pack('<4s',    b'PK\x01\x02')
        cdh += struct.pack('<H',    20)
        cdh += struct.pack('<H',    20)
        cdh += struct.pack('<H',    0)
        cdh += struct.pack('<H',    compression)
        cdh += struct.pack('<H',    1000)
        cdh += struct.pack('<H',    1000)
        cdh += struct.pack('<L',    binascii.crc32(content_bytes) & 0xffffffff)
        cdh += struct.pack('<L',    len(content_bytes))
        cdh += struct.pack('<L',    len(content_bytes))
        cdh += struct.pack('<H',    len(filename_bytes))
        cdh += struct.pack('<H',    0)
        cdh += struct.pack('<H',    0)
        cdh += struct.pack('<H',    0)
        cdh += struct.pack('<H',    0)
        cdh += struct.pack('<L',    0x81800000)
        cdh += struct.pack('<L',    lfh_offset)
        cdh += filename_bytes
        
        return cdh

    def create_eocd(cd_offset, cd_size, entry_count, comment=b''):
        """Create End of Central Directory record with optional comment."""
        eocd = struct.pack('<4s',   b'PK\x05\x06')
        eocd += struct.pack('<H',   0)
        eocd += struct.pack('<H',   0)
        eocd += struct.pack('<H',   entry_count)
        eocd += struct.pack('<H',   entry_count)
        eocd += struct.pack('<L',   cd_size)
        eocd += struct.pack('<L',   cd_offset)
        eocd += struct.pack('<H',   len(comment))
        eocd += comment
        
        return eocd
    zip_data = b''
    main_cd_entries = []
    

    lfh1 = create_lfh("normal.txt", "This is a normal file with LFH and CDH")
    offset1 = len(zip_data)
    zip_data += lfh1
    main_cd_entries.append(("normal.txt", "This is a normal file with LFH and CDH", offset1))

    lfh2 = create_lfh("orphaned_alone.txt", "This LFH has no CDH anywhere!")
    zip_data += lfh2

    lfh3 = create_lfh("orphaned_with_cdh.txt", "This LFH has a CDH but CDH is in EOCD comment")
    offset3 = len(zip_data)
    zip_data += lfh3
    
    lfh4 = create_lfh("normal2.txt", "Second normal file")
    offset4 = len(zip_data)
    zip_data += lfh4
    main_cd_entries.append(("normal2.txt", "Second normal file", offset4))

    main_cd_offset = len(zip_data)
    main_cd_data = b''
    for filename, content, offset in main_cd_entries:
        cdh = create_cdh(filename, content, offset)
        main_cd_data += cdh
    zip_data += main_cd_data

    orphaned_cd_data = b''

    orphaned_cdh1 = create_cdh("orphaned_with_cdh.txt", "This LFH has a CDH but CDH is in EOCD comment", offset3)
    orphaned_cd_data += orphaned_cdh1

    orphaned_cdh2 = create_cdh("nonexistent.txt", "This CDH points to nowhere", 0x99999999)
    orphaned_cd_data += orphaned_cdh2
    
    comment_prefix = b"Hidden CDHs: "
    eocd_comment = comment_prefix + orphaned_cd_data

    main_eocd = create_eocd(main_cd_offset, len(main_cd_data), len(main_cd_entries), eocd_comment)
    zip_data += main_eocd
    return zip_data

def main():
    zip_data = create_complex_orphaned_zip()
    

    with open('test_complex_orphaned.zip', 'wb') as f:
        f.write(zip_data)

if __name__ == '__main__':
    main()