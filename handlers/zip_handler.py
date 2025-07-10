"""
Handler for ZIP archive operations.
Implements the BaseArchiveHandler interface for ZIP archives.
"""

import os
import zipfile
from handlers.extended_zipfile import ExtendedZipFile
from datetime import datetime
from handlers.base_handler import BaseArchiveHandler
import warnings
import sys
import binascii

warnings.filterwarnings("ignore", category=UserWarning, module="zipfile", message="Duplicate name:.*")

class ZipHandler(BaseArchiveHandler):
    """Handler for ZIP archives."""
    
    def __init__(self, orphaned_mode=False):
        """Initialize the ZIP handler.
        
        Args:
            orphaned_mode: If True, use ExtendedZipFile with orphaned entry detection.
                          If False, use standard zipfile.ZipFile.
        """
        self.orphaned_mode = orphaned_mode
    
    def _create_new_archive(self, file_path):
        """Create a new ZIP archive."""
        return ExtendedZipFile(file_path, "w", orphaned_mode=self.orphaned_mode)
    
    def _open_existing_archive(self, file_path, mode="a"):
        """Open an existing ZIP archive."""
        return ExtendedZipFile(file_path, mode, orphaned_mode=self.orphaned_mode)
    
    def _parse_extra_field(self, extra_data):
        """Parse the extra field data in ZIP headers."""
        if not extra_data:
            return {}
        
        result = {}
        pos = 0
        while pos + 4 <= len(extra_data):
            header_id = int.from_bytes(extra_data[pos:pos+2], byteorder='little')
            data_size = int.from_bytes(extra_data[pos+2:pos+4], byteorder='little')
            
            # Ensure we have enough data
            if pos + 4 + data_size > len(extra_data):
                break
            
            # Extract the data for this header
            header_data = extra_data[pos+4:pos+4+data_size]
            
            # Known header IDs
            if header_id == 0x5455:  # UT - Extended timestamp
                result['UT_timestamp'] = self._parse_ut_timestamp(header_data)
            elif header_id == 0x7875:  # ux - Unix UID/GID
                result['ux_uid_gid'] = self._parse_ux_uid_gid(header_data)
            elif header_id == 0x7075:  # Info-ZIP Unicode Path
                key = 'Unicode_Path'
                if key in result:
                    # To be able to display multiple fields with the same ID
                    key = key + str(binascii.crc32(header_data))
                result[key] = self._parse_unicode_path(header_data)
            else:
                result[f'header_0x{header_id:04x}'] = header_data.hex()
            
            pos += 4 + data_size
        
        return result

    def _parse_unicode_path(self, data):
        """Parse the Info-Zip Unicode Path extra field."""
        result = {}
        
        if len(data) >= 1:
            version = data[0]
            result['version'] = version
        if len(data) >= 5 and version == 1:
            unicodepath_crc32 = data[1:5]
            unicodepath = data[5:]
            result['path'] = unicodepath
        
        return result

    def _parse_ut_timestamp(self, data):
        """Parse the UT (extended timestamp) extra field."""
        if not data:
            return {}
        
        result = {}
        flags = data[0] if data else 0
        pos = 1
        
        # Check for each timestamp type
        if flags & 1 and pos + 4 <= len(data):  # Mod time
            mod_time = int.from_bytes(data[pos:pos+4], byteorder='little')
            result['mod_time'] = f"{mod_time} ({datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})"
            pos += 4
        
        if flags & 2 and pos + 4 <= len(data):  # Access time
            access_time = int.from_bytes(data[pos:pos+4], byteorder='little')
            result['access_time'] = f"{access_time} ({datetime.fromtimestamp(access_time).strftime('%Y-%m-%d %H:%M:%S')})"
            pos += 4
        
        if flags & 4 and pos + 4 <= len(data):  # Create time
            create_time = int.from_bytes(data[pos:pos+4], byteorder='little')
            result['create_time'] = f"{create_time} ({datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')})"
        
        return result

    def _parse_ux_uid_gid(self, data):
        """Parse the ux (Unix UID/GID) extra field."""
        result = {}
        
        if len(data) >= 1:
            version = data[0]
            result['version'] = version
        
        if len(data) >= 3 and version == 1:
            uid_size = data[1]
            if 2 + uid_size <= len(data):
                uid = int.from_bytes(data[2:2+uid_size], byteorder='little')
                result['uid'] = uid
            
            if 2 + uid_size + 1 <= len(data):
                gid_size = data[2+uid_size]
                if 2 + uid_size + 1 + gid_size <= len(data):
                    gid = int.from_bytes(data[2+uid_size+1:2+uid_size+1+gid_size], byteorder='little')
                    result['gid'] = gid
        
        return result

    def _get_compression_type_name(self, compress_type):
        """Get a human-readable name for the compression type."""
        compression_types = {
            0: "stored (no compression)",
            1: "shrunk",
            2: "reduced with compression factor 1",
            3: "reduced with compression factor 2",
            4: "reduced with compression factor 3",
            5: "reduced with compression factor 4",
            6: "imploded",
            7: "reserved",
            8: "deflated",
            9: "enhanced deflated",
            10: "PKWare DCL imploded",
            12: "BZIP2",
            14: "LZMA",
            18: "IBM TERSE",
            19: "IBM LZ77 z",
            97: "WavPack",
            98: "PPMd version I, Rev 1"
        }
        return compression_types.get(compress_type, f"unknown ({compress_type})")

    def _set_file_permissions(self, info, mode=None, is_dir=False, is_symlink=False, preserve_type=False, orig_attr=None, uid=None, gid=None, override_unicode_path=None):
        """Set file permissions and type for a ZipInfo object."""
        # Define file type constants
        S_IFREG = 0o100000  # Regular file
        S_IFDIR = 0o040000  # Directory
        S_IFLNK = 0o120000  # Symbolic link
        DOS_ARCHIVE    = 0x20  # Archive bit
        DOS_DIRECTORY  = 0x10  # Directory
        DOS_HIDDEN     = 0x02  # Hidden
        DOS_READONLY   = 0x01  # Read-only
        # Default permissions if not specified
        if mode is None:
            if is_dir:
                mode = 0o775
            elif is_symlink:
                mode = 0o755
            else:
                mode = 0o644

        # TODO: Should DOS_ARCHIVE default? "file has changed since last backup"
        dos_attr = 0x00
        if is_dir:
            dos_attr = DOS_DIRECTORY
        
        # Apply file type bits
        if preserve_type and orig_attr is not None:
            # Extract original file type bits (top 4 bits of mode)
            type_bits = orig_attr >> 16 & 0o170000
            full_mode = (mode & 0o7777) | type_bits
        else:
            # Set appropriate file type bits based on entry type
            if is_symlink:
                full_mode = (mode & 0o7777) | S_IFLNK
            elif is_dir:
                full_mode = (mode & 0o7777) | S_IFDIR
            else:
                full_mode = (mode & 0o7777) | S_IFREG
        
        # Combine Unix permission bits (high 16 bits) with MS-DOS attributes (low byte)
        info.external_attr = (full_mode << 16) | dos_attr
        # Add UID/GID to extra field if specified
        if uid is not None or gid is not None:
            # Use defaults if only one is specified
            if uid is None:
                uid = 0
            if gid is None:
                gid = 0
            
            # Add the "Info-ZIP Unix Extra Field (type 3)" for UID/GID
            self._add_uid_gid_extra_field(info, uid, gid)
        
        # Add the "Info-ZIP Unix Extra Field (type 3)" for Unicode Path
        # TODO: break out from this function? Always set this?
        if override_unicode_path != None:
            self._add_unicode_path_extra_field(info, info.filename, override_unicode_path)
        
        return info

    def _add_unicode_path_extra_field(self, info, path, override_path=None):
        """Add Unicode Path to ZipInfo extra field using Info-ZIP Unix format.
        
        This uses the "Info-ZIP Unix Extra Field (type 3)" format with header ID 0x7075.
        
        Args:
            info: The ZipInfo object to modify
            path: The unicode version of the entry path
        """
        # Info-ZIP Unix Extra Field (type 3) header ID
        HEADER_ID = 0x7075
        
        # Current extra data (preserve any existing fields)
        extra_data = info.extra if hasattr(info, 'extra') and info.extra else b''
        
        # Remove any existing Unicode Path fields (to avoid duplicates)
        pos = 0
        new_extra = bytearray()
        
        while pos + 4 <= len(extra_data):
            header_id = int.from_bytes(extra_data[pos:pos+2], byteorder='little')
            data_size = int.from_bytes(extra_data[pos+2:pos+4], byteorder='little')
            
            # Skip over existing Unix UID/GID field if present
            if header_id == HEADER_ID:
                pos += 4 + data_size
                continue
            
            # Copy other fields
            field_size = 4 + data_size
            new_extra.extend(extra_data[pos:pos+field_size])
            pos += field_size
        
        # Format: Version(1) + Size(1) + NameCRC32 + UnicodeName
        # Version is always 1 in this implementation
        version = 1
        
        # Determine minimum bytes needed for UID and GID
        path_bytes = self.get_raw_bytes(path)
        path_unicode = path_bytes

        # Allow overriding Unicode Path (to test file.txt in LFH vs ../../../file.txt in Unicode Path)
        if override_path != None:
            path_unicode = self.get_raw_bytes(override_path)
        
        # CRC32 of path
        path_crc32 = binascii.crc32(path_bytes)
        
        # Create the field data
        field_data = bytearray()
        field_data.append(version)  # Version
        field_data.extend(path_crc32.to_bytes(4, byteorder='little'))  # NameCRC32
        field_data.extend(path_unicode)  # UnicodeName
        
        # Create the header (ID + size + data)
        header = bytearray()
        header.extend(HEADER_ID.to_bytes(2, byteorder='little'))  # Header ID
        header.extend(len(field_data).to_bytes(2, byteorder='little'))  # Data size
        header.extend(field_data)  # Field data
        
        # Append the new field to the extra data
        new_extra.extend(header)
        
        # Update the ZipInfo extra field
        info.extra = bytes(new_extra)

    def _add_uid_gid_extra_field(self, info, uid, gid):
        """Add UID/GID to ZipInfo extra field using Info-ZIP Unix format.
        
        This uses the "Info-ZIP Unix Extra Field (type 3)" format with header ID 0x7875.
        
        Args:
            info: The ZipInfo object to modify
            uid: User ID
            gid: Group ID
        """
        # Info-ZIP Unix Extra Field (type 3) header ID
        HEADER_ID = 0x7875
        
        # Current extra data (preserve any existing fields)
        extra_data = info.extra if hasattr(info, 'extra') and info.extra else b''
        
        # Remove any existing Unix UID/GID fields (to avoid duplicates)
        pos = 0
        new_extra = bytearray()
        
        while pos + 4 <= len(extra_data):
            header_id = int.from_bytes(extra_data[pos:pos+2], byteorder='little')
            data_size = int.from_bytes(extra_data[pos+2:pos+4], byteorder='little')
            
            # Skip over existing Unix UID/GID field if present
            if header_id == HEADER_ID:
                pos += 4 + data_size
                continue
            
            # Copy other fields
            field_size = 4 + data_size
            new_extra.extend(extra_data[pos:pos+field_size])
            pos += field_size
        
        # Format: Version(1) + UID Size(1) + UID + GID Size(1) + GID
        # Version is always 1 in this implementation
        version = 1
        
        # Determine minimum bytes needed for UID and GID
        uid_bytes = uid.to_bytes((uid.bit_length() + 7) // 8 or 1, byteorder='little')
        gid_bytes = gid.to_bytes((gid.bit_length() + 7) // 8 or 1, byteorder='little')
        
        # Limit sizes to 255 bytes (field limitation)
        uid_bytes = uid_bytes[:255]
        gid_bytes = gid_bytes[:255]
        
        # Create the field data
        field_data = bytearray()
        field_data.append(version)  # Version
        field_data.append(len(uid_bytes))  # UID size
        field_data.extend(uid_bytes)  # UID
        field_data.append(len(gid_bytes))  # GID size
        field_data.extend(gid_bytes)  # GID
        
        # Create the header (ID + size + data)
        header = bytearray()
        header.extend(HEADER_ID.to_bytes(2, byteorder='little'))  # Header ID
        header.extend(len(field_data).to_bytes(2, byteorder='little'))  # Data size
        header.extend(field_data)  # Field data
        
        # Append the new field to the extra data
        new_extra.extend(header)
        
        # Update the ZipInfo extra field
        info.extra = bytes(new_extra)

    def _describe_zip_flags(self, flags):
        """Describe the meaning of ZIP general purpose bit flags."""
        descriptions = []
        
        if flags & 0x0001:
            descriptions.append("encrypted")
        if flags & 0x0002:
            if flags & 0x0004:
                descriptions.append("super-fast compression")
            else:
                descriptions.append("maximum compression")
        if flags & 0x0004 and not (flags & 0x0002):
            descriptions.append("fast compression")
        if flags & 0x0008:
            descriptions.append("data descriptor follows")
        if flags & 0x0010:
            descriptions.append("enhanced deflation")
        if flags & 0x0020:
            descriptions.append("compressed patched data")
        if flags & 0x0040:
            descriptions.append("strong encryption")
        if flags & 0x0800:
            descriptions.append("UTF-8 encoding")
        if flags & 0x1000:
            descriptions.append("enhanced compression")
        if flags & 0x2000:
            descriptions.append("encrypted central directory")
        
        return ", ".join(descriptions) if descriptions else "none"

    def _decode_dos_time(self, time_value):
        """Decode a DOS time value to a human-readable format."""
        hours = (time_value >> 11) & 0x1F
        minutes = (time_value >> 5) & 0x3F
        seconds = (time_value & 0x1F) * 2
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _decode_dos_date(self, date_value):
        """Decode a DOS date value to a human-readable format."""
        year = ((date_value >> 9) & 0x7F) + 1980
        month = (date_value >> 5) & 0x0F
        day = date_value & 0x1F
        return f"{year}-{month:02d}-{day:02d}"

    def _compare_lfh_cdh_fields(self, entry, lfh, cdh):
        """Compare LFH and CDH fields using actual raw field values with zip_file context."""
        
        # Compare actual raw fields
        fields_to_compare = [
            ('version_needed', cdh.raw_fields['version_needed'], lfh.raw_fields['version_needed']),
            ('flags', cdh.raw_fields['flags'], lfh.raw_fields['flags']),
            ('compression_method', cdh.raw_fields['compression_method'], lfh.raw_fields['compression_method']),
            ('last_mod_time', cdh.raw_fields['last_mod_time'], lfh.raw_fields['last_mod_time']),
            ('last_mod_date', cdh.raw_fields['last_mod_date'], lfh.raw_fields['last_mod_date']),
            ('crc_32', cdh.raw_fields['crc32'], lfh.raw_fields['crc32']),
            ('compressed_size', cdh.raw_fields['compressed_size'], lfh.raw_fields['compressed_size']),
            ('uncompressed_size', cdh.raw_fields['uncompressed_size'], lfh.raw_fields['uncompressed_size']),
            ('filename', cdh.zipinfo.filename, lfh.zipinfo.filename),
        ]
        
        for field_name, cdh_value, lfh_value in fields_to_compare:
            match = "MATCH" if cdh_value == lfh_value else "MISMATCH"
            print(f"    {field_name:<20}: {match} - CDH: {cdh_value}, LFH: {lfh_value}")

    def _list_long(self, args, zip_file):
        """Enhanced verbose listing using ExtendedZipFile capabilities."""
        print(f"Verbose header information for {args.file}:")
        
        # Process each extended entry
        extended_entries = zip_file.get_extended_infolist()
        
        for entry in extended_entries:
            display_name = zip_file.get_display_name(entry)
            print(f"\nFile: {display_name}")
            print(f"{'-'*70}")
            
            if entry.is_orphaned_lfh:
                if hasattr(entry, 'cdh_filename') and entry.cdh_filename:
                    print("  Status: ORPHANED LFH (not in main central directory)")
                else:
                    print("  Status: ORPHANED LFH/CDH (not in any central directory)")
            else:
                print("  Status: Standard entry")
            
            # Show LFH information if available
            if hasattr(entry, 'lfh_offset') and entry.lfh_offset is not None:
                lfh = zip_file._find_lfh_by_offset(entry.lfh_offset)
                if lfh:
                    print(f"\n  Local File Header (offset: {entry.lfh_offset}):")
                    self._display_lfh(lfh)
            else:
                if hasattr(entry, 'header_offset') and entry.header_offset is not None:
                    lfh = zip_file._find_lfh_by_offset(entry.header_offset)
                    if lfh:
                        print(f"\n  Local File Header (offset: {entry.header_offset}):")
                        self._display_lfh(lfh)
            
            # Show CDH information if available  
            if hasattr(entry, 'cdh_filename') and entry.cdh_filename:
                # Find the CDH entry for this file
                cdh_info = self._find_cdh_for_entry(entry, zip_file)
                if cdh_info:
                    print(f"\n  Central Directory Header (offset: {cdh_info.offset}):")
                    self._display_cdh(entry, cdh_info)
                    
                    # Show field comparison if we have both LFH and CDH
                    if hasattr(entry, 'lfh_offset') and entry.lfh_offset is not None:
                        lfh = zip_file._find_lfh_by_offset(entry.lfh_offset)
                        if lfh:
                            print(f"\n  Header Field Comparison (CDH vs LFH):")
                            # We need to pass the zip_file context to access parsed_cdhs
                            self._compare_lfh_cdh_fields(entry, lfh, cdh_info)
            
            print(f"{'-'*70}")

    def _display_lfh(self, lfh):
        """Display LFH."""
        raw = lfh.raw_fields
        zipinfo = lfh.zipinfo
    
        print(f"    signature           : {raw['signature'].hex()}")
        print(f"    version_needed      : {raw['version_needed']}")
        print(f"    flags               : {raw['flags']} ({self._describe_zip_flags(raw['flags'])})")
        print(f"    compression_method  : {raw['compression_method']} ({self._get_compression_type_name(raw['compression_method'])})")
        print(f"    last_mod_time       : {raw['last_mod_time']} ({self._decode_dos_time(raw['last_mod_time'])})")
        print(f"    last_mod_date       : {raw['last_mod_date']} ({self._decode_dos_date(raw['last_mod_date'])})")
        print(f"    crc_32              : {raw['crc32']}")
        print(f"    compressed_size     : {raw['compressed_size']}")
        print(f"    uncompressed_size   : {raw['uncompressed_size']}")
        print(f"    filename_length     : {raw['filename_length']}")
        print(f"    extra_field_length  : {raw['extra_length']}")
        print(f"    filename            : {zipinfo.filename}")
        if lfh.raw_extra:
            hex_extra = ' '.join(f'{b:02x}' for b in lfh.raw_extra)
            print(f"    extra_hex           : {hex_extra}")
            extra_parsed = self._parse_extra_field(lfh.raw_extra)
            if extra_parsed:
                print(f"    extra_parsed        :")
                for k, v in extra_parsed.items():
                    if isinstance(v, dict):
                        print(f"      {k}:")
                        for sk, sv in v.items():
                            print(f"        {sk}: {sv}")
                    else:
                        print(f"      {k}: {v}")

    def _display_cdh(self, entry, cdh_info):
        """Display CDH using raw fields (similar to _display_lfh)."""
        raw = cdh_info.raw_fields
        zipinfo = cdh_info.zipinfo
        
        print(f"    signature           : {raw['signature'].hex()}")
        print(f"    version_made_by     : {raw['version_made_by']}")
        print(f"    version_needed      : {raw['version_needed']}")
        print(f"    flags               : {raw['flags']} ({self._describe_zip_flags(raw['flags'])})")
        print(f"    compression_method  : {raw['compression_method']} ({self._get_compression_type_name(raw['compression_method'])})")
        print(f"    last_mod_time       : {raw['last_mod_time']} ({self._decode_dos_time(raw['last_mod_time'])})")
        print(f"    last_mod_date       : {raw['last_mod_date']} ({self._decode_dos_date(raw['last_mod_date'])})")
        print(f"    crc_32              : {raw['crc32']}")
        print(f"    compressed_size     : {raw['compressed_size']}")
        print(f"    uncompressed_size   : {raw['uncompressed_size']}")
        print(f"    filename_length     : {raw['filename_length']}")
        print(f"    extra_field_length  : {raw['extra_length']}")
        print(f"    comment_length      : {raw['comment_length']}")
        print(f"    disk_number_start   : {raw['disk_start']}")
        print(f"    internal_file_attr  : {raw['internal_attr']}")
        mode = raw['external_attr'] >> 16
        perm_str = self.format_mode(mode)
        print(f"    external_file_attr  : {raw['external_attr']} (Unix mode: {oct(mode)} {perm_str})")
        print(f"    local_header_offset : {raw['lfh_offset']}")
        print(f"    filename            : {zipinfo.filename}")
        
        # Show extra field if present
        if raw['extra']:
            hex_extra = ' '.join(f'{b:02x}' for b in raw['extra'])
            print(f"    extra_hex           : {hex_extra}")
            extra_parsed = self._parse_extra_field(raw['extra'])
            if extra_parsed:
                print(f"    extra_parsed        :")
                for k, v in extra_parsed.items():
                    if isinstance(v, dict):
                        print(f"      {k}:")
                        for sk, sv in v.items():
                            print(f"        {sk}: {sv}")
                    else:
                        print(f"      {k}: {v}")

    def _find_cdh_for_entry(self, entry, zip_file):
        """Find CDH information for an entry."""
        # For standard entries, we know they have CDH info
        if not entry.is_orphaned_lfh:
            # Try to find the CDH in parsed_cdhs that corresponds to this entry
            for cdh in zip_file.parsed_cdhs:
                if (hasattr(entry, 'header_offset') and 
                    cdh.lfh_offset == entry.header_offset):
                    return cdh  # Return the full ParsedCDH object
        else:
            # For orphaned entries, check if we found a matching CDH
            # TODO: What if multiple CDH reference the same LFH?
            if hasattr(entry, 'lfh_offset'):
                for cdh in zip_file.parsed_cdhs:
                    if cdh.lfh_offset == entry.lfh_offset:
                        return cdh  # Return the full ParsedCDH object
        return None

    def add(self, args):
        """Add a file or symlink to the ZIP archive."""
        # Create archive or open existing
        if os.path.exists(args.file):            
            archive = self._open_existing_archive(args.file)
            
            # --content-directory should replace if exists
            file_exists = args.path in archive.namelist()
            if file_exists and getattr(args, 'content_directory', None) is not None:
                # Create temporary args for replace
                replace_args = type('Args', (), {
                    'file': args.file,
                    'path': args.path,
                    'content': args.content,
                    'content_file': args.content_file,
                    'verbose': args.verbose,
                    'require_content': False,
                    'mode': args.mode if hasattr(args, 'mode') else None,
                    'mtime': args.mtime if hasattr(args, 'mtime') else None,
                    'symlink': args.symlink if hasattr(args, 'symlink') else None,
                    'hardlink': args.hardlink if hasattr(args, 'hardlink') else None,
                    'setuid': args.setuid if hasattr(args, 'setuid') else False,
                    'setgid': args.setgid if hasattr(args, 'setgid') else False,
                    'sticky': args.sticky if hasattr(args, 'sticky') else False,
                    'unicodepath': args.unicodepath if hasattr(args, 'unicodepath') else None
                })
                
                return self.replace(replace_args)
        else:
            archive = self._create_new_archive(args.file)
        
        try:
            # Process symlink
            if args.symlink:
                info = zipfile.ZipInfo(args.path)
                
                # Set file permissions for symlink
                self._set_file_permissions(
                    info,
                    mode=args.mode, 
                    is_symlink=True,
                    uid=args.uid if hasattr(args, 'uid') else None,
                    gid=args.gid if hasattr(args, 'gid') else None,
                    override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                )
                
                # Set modification time if specified
                if args.mtime:
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                # Set symlink target as the file content
                archive.writestr(info, args.symlink)
                
                if args.verbose:
                    print(f"Added symlink {args.path} -> {args.symlink} to {args.file}")
            
            # Process hardlink
            elif args.hardlink:
                # ZIP still doesn't support hardlinks properly
                print("Warning: ZIP format doesn't support hardlinks. "
                    "Creating a regular file instead.")
                info = zipfile.ZipInfo(args.path)
                
                # Set file permissions for regular file
                self._set_file_permissions(
                    info,
                    mode=args.mode, 
                    is_dir=False,
                    uid=args.uid if hasattr(args, 'uid') else None,
                    gid=args.gid if hasattr(args, 'gid') else None,
                    override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                )
                
                # Set modification time if specified
                if args.mtime:
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                archive.writestr(info, args.hardlink)
            
            # Process regular file
            else:
                # For ZIP, we can control the basic info using ZipInfo
                info = zipfile.ZipInfo(args.path)
                
                # Determine if this is a directory entry
                is_dir = args.path.endswith('/')
                
                # Set file permissions
                self._set_file_permissions(
                    info,
                    mode=args.mode, 
                    is_dir=is_dir,
                    uid=args.uid if hasattr(args, 'uid') else None,
                    gid=args.gid if hasattr(args, 'gid') else None,
                    override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                )
                
                # Set modification time if specified
                if args.mtime:
                    # Convert to tuple for ZIP
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                # Set special bits if requested
                if args.setuid or args.setgid or args.sticky:
                    mode = args.mode if args.mode else (0o755 if is_dir else 0o644)
                    mode = self.apply_special_bits(mode, args)
                    # Apply again with the special bits
                    self._set_file_permissions(
                        info,
                        mode=mode, 
                        is_dir=is_dir,
                        uid=args.uid if hasattr(args, 'uid') else None,
                        gid=args.gid if hasattr(args, 'gid') else None,
                        override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                    )
                
                # Get content from either --content or --content-file
                try:
                    content = self.get_content(args)
                    archive.writestr(info, content)
                    
                    if args.verbose:
                        if args.content_file:
                            print(f"Added {args.path} with content from {args.content_file} to {args.file}")
                        else:
                            print(f"Added {args.path} to {args.file}")
                except (ValueError, FileNotFoundError) as e:
                    print(f"Error: {e}")
                    return
                
        finally:
            archive.close()

    def replace(self, args):
        """Replace a file in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
                
        self.remove(args)
        self.add(args)
        if args.verbose:
            if args.content_file:
                print(f"Replaced {args.path} with content from {args.content_file} in {args.file}")
            else:
                print(f"Replaced {args.path} in {args.file}")
        return

    def append(self, args):
        """Append content to a file in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Get content to append from either --content or --content-file
        try:
            append_content = self.get_content(args)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}")
            return
        
        # If neither content nor content-file is specified, show an error
        if not args.content and not args.content_file and args.require_content:
            print("Error: Either --content or --content-file must be specified")
            return
        
        # Extract the file, append content, and replace it
        with self._open_existing_archive(args.file, "r") as zip_ref:
            if args.path not in zip_ref.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Extract the file content
            existing_content = zip_ref.read(args.path)
            
            # Append content
            new_content = existing_content + append_content
            
            # Create temporary args for replace
            replace_args = type('Args', (), {
                'file': args.file,
                'path': args.path,
                'content': new_content,
                'content_file': None,
                'verbose': args.verbose,
                'require_content': False,
                'mode': args.mode if hasattr(args, 'mode') else None,
                'mtime': args.mtime if hasattr(args, 'mtime') else None,
                'symlink': args.symlink if hasattr(args, 'symlink') else None,
                'hardlink': args.hardlink if hasattr(args, 'hardlink') else None,
                'setuid': args.setuid if hasattr(args, 'setuid') else False,
                'setgid': args.setgid if hasattr(args, 'setgid') else False,
                'sticky': args.sticky if hasattr(args, 'sticky') else False
            })
            
            # Call replace with the new content
            self.replace(replace_args)
        
        if args.verbose:
            if args.content_file:
                print(f"Appended content from {args.content_file} to {args.path} in {args.file}")
            else:
                print(f"Appended to {args.path} in {args.file}")
    
    def modify(self, args):
        """Modify file attributes in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Check for both symlink and hardlink options
        if args.symlink and args.hardlink:
            print("Error: Cannot specify both --symlink and --hardlink")
            return
        
        # For ZIP, we need to extract, modify, and rewrite
        with self._open_existing_archive(args.file, "r") as zip_in:
            if args.path not in zip_in.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Extract the file content (if we're not converting to a link)
            content = zip_in.read(args.path) if not (args.symlink or args.hardlink) else None
            
            # Get the original info
            orig_info = zip_in.getinfo(args.path)
            
            # Get all other entries
            entries = [entry for entry in zip_in.get_extended_infolist() 
                    if entry.filename != args.path]
            
            # Create a new ZIP file
            with self._create_new_archive(args.file + ".tmp") as zip_out:
                # Copy all the other entries
                for entry in entries:
                    zip_out.writestr(entry, zip_in.read(entry))
                
                # Create new info
                info = zipfile.ZipInfo(args.path)
                info.date_time = orig_info.date_time if args.mtime is None else datetime.fromtimestamp(args.mtime).timetuple()[:6]
                info.comment = orig_info.comment
                info.extra = orig_info.extra
                info.create_system = orig_info.create_system
                
                # Convert to symlink
                if args.symlink:
                    # Set file permissions for symlink
                    self._set_file_permissions(
                        info,
                        mode=args.mode, 
                        is_symlink=True,
                        uid=args.uid if hasattr(args, 'uid') else None,
                        gid=args.gid if hasattr(args, 'gid') else None,
                        override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                    )
                    
                    # Set symlink target as the file content
                    zip_out.writestr(info, args.symlink)
                    
                    if args.verbose:
                        print(f"Converting {args.path} to symlink -> {args.symlink}")
                
                # Convert to hardlink - ZIP doesn't support hardlinks natively
                elif args.hardlink:
                    print("Warning: ZIP format doesn't support hardlinks. "
                        "Creating a file with hardlink target as content.")
                    
                    # Set file permissions, preserving original type if possible
                    is_dir = args.path.endswith('/')
                    
                    self._set_file_permissions(
                        info,
                        mode=args.mode, 
                        is_dir=is_dir, 
                        preserve_type=True, 
                        orig_attr=orig_info.external_attr,
                        uid=args.uid if hasattr(args, 'uid') else None,
                        gid=args.gid if hasattr(args, 'gid') else None,
                        override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                    )
                    
                    # Set special bits if requested
                    if args.setuid or args.setgid or args.sticky:
                        mode = (orig_info.external_attr >> 16) & 0o777
                        if args.mode:
                            mode = args.mode
                        mode = self.apply_special_bits(mode, args)
                        self._set_file_permissions(
                            info,
                            mode=mode, 
                            is_dir=is_dir, 
                            preserve_type=True, 
                            orig_attr=orig_info.external_attr,
                            uid=args.uid if hasattr(args, 'uid') else None,
                            gid=args.gid if hasattr(args, 'gid') else None,
                            override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                        )
                    
                    # Add the file with hardlink target as content
                    zip_out.writestr(info, args.hardlink)
                
                # Regular attribute modification
                else:
                    # Determine if this is a directory
                    is_dir = args.path.endswith('/')
                    
                    # Set file permissions, preserving file type
                    self._set_file_permissions(
                        info,
                        mode=args.mode, 
                        preserve_type=True, 
                        orig_attr=orig_info.external_attr,
                        uid=args.uid if hasattr(args, 'uid') else None,
                        gid=args.gid if hasattr(args, 'gid') else None,
                        override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                    )
                    
                    # Set special bits if requested
                    if args.setuid or args.setgid or args.sticky:
                        # Get current mode from external_attr
                        mode = (orig_info.external_attr >> 16) & 0o777
                        if args.mode:
                            mode = args.mode
                        mode = self.apply_special_bits(mode, args)
                        self._set_file_permissions(
                            info,
                            mode=mode, 
                            preserve_type=True, 
                            orig_attr=orig_info.external_attr,
                            uid=args.uid if hasattr(args, 'uid') else None,
                            gid=args.gid if hasattr(args, 'gid') else None,
                            override_unicode_path=args.unicodepath if hasattr(args, 'unicodepath') else None
                        )
                    
                    # Add the modified entry with original content
                    zip_out.writestr(info, content)
        
        # Replace the original file
        os.remove(args.file)
        os.rename(args.file + ".tmp", args.file)
        
        if args.verbose:
            if args.symlink:
                print(f"Modified {args.path} to be a symlink to {args.symlink} in {args.file}")
            elif args.hardlink:
                print(f"Modified {args.path} to be a hardlink to {args.hardlink} in {args.file}")
            else:
                print(f"Modified attributes of {args.path} in {args.file}")

    def remove(self, args):
        """Remove a file from the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Check if the archive exists
        try:
            with self._open_existing_archive(args.file, "r") as zip_in:
                # Get the list of entries
                entries = zip_in.get_extended_infolist()

                # Recursive
                is_recursive = bool(args.recursive) if hasattr(args, 'recursive') else True
                
                # Check if the path exists in the archive
                paths_to_remove = []
                for entry in entries:
                    # Exact match = remove path
                    # Recursive + empty path = remove root
                    # Recursive + path = remove path/
                    if entry.filename == args.path or (is_recursive and args.path == "") or (is_recursive and entry.filename.startswith(args.path.rstrip("/") + "/")):
                        paths_to_remove.append(entry.filename)
                
                if not paths_to_remove:
                    print(f"Error: {args.path} not found in the archive")
                    return
                
                # Get all entries except those we want to remove
                entries_to_keep = [entry for entry in entries 
                                if entry.filename not in paths_to_remove]
                
                # Create a new ZIP file
                with self._create_new_archive(args.file + ".tmp") as zip_out:
                    # Copy all the other entries
                    for entry in entries_to_keep:
                        zip_out.writestr(entry, zip_in.read(entry))
            
            # Replace the original file
            os.remove(args.file)
            os.rename(args.file + ".tmp", args.file)
            
            if args.verbose:
                if len(paths_to_remove) == 1:
                    print(f"Removed {paths_to_remove[0]} from {args.file}")
                else:
                    print(f"Removed {len(paths_to_remove)} entries from {args.file}")
                    if args.verbose:
                        for path in paths_to_remove:
                            print(f"  - {path}")
        
        except zipfile.BadZipFile as e:
            print(f"Error: {args.file} is not a valid ZIP file ({e})")

    def list(self, args):
        """List the contents of the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        try:
            with self._open_existing_archive(args.file, "r") as zip_file:
                entries = zip_file.get_extended_infolist()

                if not entries:
                    print(f"Archive {args.file} is empty")
                    return

                # Very verbose listing with all header information
                if hasattr(args, 'longlong') and args.longlong or args.long == 2:
                    self._list_long(args, zip_file)
                
                if args.long:
                    print(f"{'Permissions':<12} {'Size':>10} {'Modified':>20} {'Name'}")
                    print(f"{'-'*12} {'-'*10} {'-'*20} {'-'*30}")
                else:
                    print(f"Contents of {args.file}:")
                
                # Print entries
                for entry in entries:
                    # Skip directories for simple listing
                    if not args.long and entry.filename.endswith('/'):
                        continue
                    
                    if args.long:
                        # Extract date and time
                        try:
                            date_time = datetime(*entry.date_time)
                            date_str = date_time.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception as e:
                            if args.verbose:
                                print(f"Error: invalid date in header: {entry.date_time}, {e}")
                            date_str = "INVALID_DATE"
                        
                        # Get permissions 
                        # ZIP uses the high bits of external_attr for Unix permissions
                        mode = entry.external_attr >> 16
                        perm_str = self.format_mode(mode)
                        
                        # Check if it's a symlink by looking at file mode
                        is_symlink = mode & 0o170000 == 0o120000
                        name = entry.filename

                        # Display Unicode Path if provided in extra fields                        
                        if entry.extra:
                            extra_parsed = self._parse_extra_field(entry.extra)
                            if 'Unicode_Path' in extra_parsed:
                                name = f"{name} (unicode: {extra_parsed['Unicode_Path']['path']})"
                        
                        # If it's a symlink, display target
                        if is_symlink:
                            try:
                                target = zip_file.read(entry).decode('utf-8')
                                name = f"{name} -> {target}"
                            except Exception as e:
                                pass
                        
                        print(f"{perm_str} {entry.file_size:>10} {date_str:>20} {name}")
                    else:
                        print(f"{entry.filename}")
        
        except zipfile.BadZipFile as e:
            print(f"Error: {args.file} is not a valid ZIP file ({e})")

    def read(self, args):
        """Read the contents of an entry."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        try:
            with self._open_existing_archive(args.file, "r") as zip_file:
                entries = zip_file.get_extended_infolist()
                current_index = 0
                found = False
                
                if not entries:
                    print(f"Archive {args.file} is empty")
                    return
                
                for entry in entries:
                    # Skip other entries
                    if not entry.filename == args.path:
                        continue
                    # Skip other entries until requested index is reached
                    if not args.index == current_index:
                        current_index += 1
                        continue
                    
                    found = True
                    if entry.is_dir():
                        print(f"Error: could not read {args.path}, it is a directory")
                        break
                    sys.stdout.buffer.write(zip_file.read(entry))
                    sys.stdout.buffer.flush()
                    break
            if not found:
                print(f"Error: could not find {args.path}, index {args.index} in archive")
        
        except zipfile.BadZipFile as e:
            print(f"Error: {args.file} is not a valid ZIP file ({e})")

    def extract(self, args):
        """Extract files from the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Create output directory if it doesn't exist
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir, exist_ok=True)
        
        try:
            with self._open_existing_archive(args.file, "r") as zip_file:
                # Get list of entries to extract
                entries = zip_file.get_extended_infolist()
                
                # Filter entries if a specific path is specified
                if args.path:
                    # Keep entries that match the path or are under the path directory
                    entries = [entry for entry in entries if
                            entry.filename == args.path or
                            entry.filename.startswith(args.path + "/")]
                    
                    if not entries:
                        print(f"Error: Path '{args.path}' not found in the archive")
                        return
                
                # Sort entries to ensure directories are created before files
                entries.sort(key=lambda entry: entry.filename)
                
                # Process each entry
                for entry in entries:
                    # Check if the entry is a directory
                    is_dir = entry.filename.endswith('/')
                    
                    # Determine output path - apply safety checks unless --vulnerable is specified
                    if not args.vulnerable:
                        output_path = self._sanitize_path(entry.filename, args.output_dir)
                    else:
                        output_path = os.path.join(args.output_dir, entry.filename)
                    
                    # Check if this is a symlink
                    is_symlink = False
                    symlink_target = None
                    mode = (entry.external_attr >> 16) & 0o170000
                    
                    if mode == 0o120000:  # Symlink
                        is_symlink = True
                        # Read the symlink target
                        symlink_target = zip_file.read(entry).decode('utf-8')
                        
                        # If not in vulnerable mode, create a regular file with the target as content
                        if not args.vulnerable:
                            self._create_parent_dirs(output_path)
                            with open(output_path, 'w') as f:
                                f.write(f"Symlink to: {symlink_target}")
                            if args.verbose:
                                print(f"Created file for symlink: {output_path} (points to {symlink_target})")
                            
                            # Skip to the next entry
                            continue
                    
                    # Create directory if needed
                    if is_dir:
                        if not os.path.exists(output_path):
                            os.makedirs(output_path, exist_ok=True)
                        # Set permissions - preserve by default, normalize if requested
                        if not args.normalize_permissions and not is_symlink:
                            mode = (entry.external_attr >> 16) & 0o777
                            if mode:
                                try:
                                    os.chmod(output_path, mode)
                                except:
                                    print(f"Warning: Could not set permissions for {output_path}")
                        if args.verbose:
                            print(f"Created directory: {output_path}")
                        continue
                    
                    # Create parent directories
                    self._create_parent_dirs(output_path)
                    
                    # Handle symlink in vulnerable mode
                    if is_symlink and args.vulnerable:
                        # Create a symlink
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        try:
                            os.symlink(symlink_target, output_path)
                            if args.verbose:
                                print(f"Created symlink: {output_path} -> {symlink_target}")
                        except:
                            print(f"Error creating symlink: {entry.filename}")
                            # Fall back to creating a regular file with the target as content
                            with open(output_path, 'w') as f:
                                f.write(f"Failed to create symlink to: {symlink_target}")
                    
                    # Regular file
                    elif not is_symlink:
                        # Extract the file
                        with open(output_path, 'wb') as f:
                            f.write(zip_file.read(entry))
                        if args.verbose:
                            print(f"Extracted: {output_path}")
                    
                    # Set permissions - preserve by default, normalize if requested
                    if not args.normalize_permissions and not is_symlink:
                        mode = (entry.external_attr >> 16) & 0o777
                        if mode:
                            try:
                                os.chmod(output_path, mode)
                            except:
                                print(f"Warning: Could not set permissions for {output_path}")
                
                # Print summary
                if args.verbose:
                    print(f"Extraction complete: {len(entries)} entries extracted to {args.output_dir}")
        
        except zipfile.BadZipFile as e:
            print(f"Error: {args.file} is not a valid ZIP file ({e})")
        except Exception as e:
            print(f"Error extracting {args.file}: {e}")

    def polyglot(self, args):
        """Add content to the beginning of a ZIP file and adjust all offsets.
        
        This creates a polyglot file by prepending content to an existing ZIP file
        and adjusting all offsets (central directory header offsets and end of
        central directory record) to maintain ZIP file validity.
        """
        # Get content from either --content or --content-file
        try:
            content_bytes = self.get_content(args)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}")
            return

        # If the file doesn't exist yet, create an empty ZIP file first
        if not os.path.exists(args.file):
            with self._create_new_archive(args.file) as zip_ref:
                pass  # Create empty ZIP

        # Read the existing ZIP file
        with open(args.file, 'rb') as f:
            zip_data = f.read()

        # Calculate the adjustment value (length of content to prepend)
        adjustment = len(content_bytes)

        # Find the End of Central Directory (EOCD) record
        eocd_offset = None
        for i in range(len(zip_data) - 22, 0, -1):
            if zip_data[i:i+4] == b'PK\x05\x06':
                eocd_offset = i
                break

        if eocd_offset is None:
            print("Error: Could not find End of Central Directory record")
            return

        # Extract central directory offset from EOCD
        cd_offset = int.from_bytes(zip_data[eocd_offset+16:eocd_offset+20], byteorder='little')

        # Create modified version with adjusted offsets
        result = bytearray()
        
        # 1. Prepend the content
        result.extend(content_bytes)
        
        # 2. Copy the ZIP data up to the Central Directory
        result.extend(zip_data[:cd_offset])
        
        # 3. Process and adjust Central Directory
        cd_data = zip_data[cd_offset:eocd_offset]
        pos = 0
        while pos < len(cd_data):
            # Check for Central Directory Header signature
            if cd_data[pos:pos+4] == b'PK\x01\x02':
                # Get entry information
                filename_len = int.from_bytes(cd_data[pos+28:pos+30], byteorder='little')
                extra_len = int.from_bytes(cd_data[pos+30:pos+32], byteorder='little')
                comment_len = int.from_bytes(cd_data[pos+32:pos+34], byteorder='little')
                
                # Get local header offset
                old_offset = int.from_bytes(cd_data[pos+42:pos+46], byteorder='little')
                
                # Adjust local header offset
                new_offset = old_offset + adjustment
                
                # Update offset in the CD entry
                result.extend(cd_data[pos:pos+42])
                result.extend(new_offset.to_bytes(4, byteorder='little'))
                result.extend(cd_data[pos+46:pos+46+filename_len+extra_len+comment_len])
                
                # Move to next entry
                pos += 46 + filename_len + extra_len + comment_len
            else:
                # Not a valid CD entry, just copy and advance
                result.append(cd_data[pos])
                pos += 1
        
        # 4. Adjust End of Central Directory record
        new_cd_offset = cd_offset + adjustment
        result.extend(zip_data[eocd_offset:eocd_offset+16])
        result.extend(new_cd_offset.to_bytes(4, byteorder='little'))
        result.extend(zip_data[eocd_offset+20:])
        
        # Write the modified ZIP file
        with open(args.file, 'wb') as f:
            f.write(result)
        
        if args.verbose:
            print(f"Added {len(content_bytes)} bytes to the beginning of {args.file}")
            print(f"Adjusted all ZIP offsets by {adjustment} bytes")