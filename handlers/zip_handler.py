"""
Handler for ZIP archive operations.
Implements the BaseArchiveHandler interface for ZIP archives.
"""

import os
import zipfile
from datetime import datetime
from handlers.base_handler import BaseArchiveHandler
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="zipfile", message="Duplicate name:.*")

class ZipHandler(BaseArchiveHandler):
    """Handler for ZIP archives."""
    
    def __init__(self):
        """Initialize the ZIP handler."""
        pass
    
    def _create_new_archive(self, file_path):
        """Create a new ZIP archive."""
        return zipfile.ZipFile(file_path, "w")
    
    def _open_existing_archive(self, file_path, mode="a"):
        """Open an existing ZIP archive."""
        return zipfile.ZipFile(file_path, mode)
    
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
            elif header_id == 0x000A:  # NTFS
                result['NTFS'] = self._parse_ntfs_extra(header_data)
            elif header_id == 0x5855:  # Info-ZIP Unix
                result['Info-ZIP_Unix'] = self._parse_infozip_unix(header_data)
            else:
                result[f'header_0x{header_id:04x}'] = header_data.hex()
            
            pos += 4 + data_size
        
        return result

    def _parse_eocd_record(self, data):
        """Parse the End of Central Directory record."""
        if len(data) < 22:
            return {'error': 'Data too short for EOCD record'}
        
        fields = {
            'signature': data[0:4].hex(),
            'disk_number': int.from_bytes(data[4:6], byteorder='little'),
            'cd_disk': int.from_bytes(data[6:8], byteorder='little'),
            'disk_entries': int.from_bytes(data[8:10], byteorder='little'),
            'cd_entries': int.from_bytes(data[10:12], byteorder='little'),
            'cd_size': int.from_bytes(data[12:16], byteorder='little'),
            'cd_offset': int.from_bytes(data[16:20], byteorder='little'),
            'comment_length': int.from_bytes(data[20:22], byteorder='little')
        }
        
        return fields

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

    def _parse_central_directory_header(self, data):
        """Parse the central directory header of a ZIP entry."""
        if len(data) < 46:
            return {'error': 'Data too short for central directory header'}
        
        fields = {
            'signature': data[0:4].hex(),
            'version_made_by': int.from_bytes(data[4:6], byteorder='little'),
            'version_needed': int.from_bytes(data[6:8], byteorder='little'),
            'flags': int.from_bytes(data[8:10], byteorder='little'),
            'compression_method': int.from_bytes(data[10:12], byteorder='little'),
            'last_mod_time': int.from_bytes(data[12:14], byteorder='little'),
            'last_mod_date': int.from_bytes(data[14:16], byteorder='little'),
            'crc_32': int.from_bytes(data[16:20], byteorder='little'),
            'compressed_size': int.from_bytes(data[20:24], byteorder='little'),
            'uncompressed_size': int.from_bytes(data[24:28], byteorder='little'),
            'filename_length': int.from_bytes(data[28:30], byteorder='little'),
            'extra_field_length': int.from_bytes(data[30:32], byteorder='little'),
            'comment_length': int.from_bytes(data[32:34], byteorder='little'),
            'disk_number_start': int.from_bytes(data[34:36], byteorder='little'),
            'internal_file_attr': int.from_bytes(data[36:38], byteorder='little'),
            'external_file_attr': int.from_bytes(data[38:42], byteorder='little'),
            'local_header_offset': int.from_bytes(data[42:46], byteorder='little')
        }
        
        return fields

    def _parse_local_file_header(self, data):
        """Parse the local file header of a ZIP entry."""
        if len(data) < 30:
            return {'error': 'Data too short for local file header'}
        
        fields = {
            'signature': data[0:4].hex(),
            'version_needed': int.from_bytes(data[4:6], byteorder='little'),
            'flags': int.from_bytes(data[6:8], byteorder='little'),
            'compression_method': int.from_bytes(data[8:10], byteorder='little'),
            'last_mod_time': int.from_bytes(data[10:12], byteorder='little'),
            'last_mod_date': int.from_bytes(data[12:14], byteorder='little'),
            'crc_32': int.from_bytes(data[14:18], byteorder='little'),
            'compressed_size': int.from_bytes(data[18:22], byteorder='little'),
            'uncompressed_size': int.from_bytes(data[22:26], byteorder='little'),
            'filename_length': int.from_bytes(data[26:28], byteorder='little'),
            'extra_field_length': int.from_bytes(data[28:30], byteorder='little')
        }
        
        # Extract filename and extra field if available
        if len(data) >= 30 + fields['filename_length']:
            fields['filename'] = data[30:30+fields['filename_length']].decode('utf-8', errors='replace')
        
        if len(data) >= 30 + fields['filename_length'] + fields['extra_field_length'] and fields['extra_field_length'] > 0:
            start = 30 + fields['filename_length']
            end = start + fields['extra_field_length']
            fields['extra'] = data[start:end]
        
        return fields

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

    def _display_zip_header_fields(self, fields):
        """Display formatted ZIP header fields."""
        for field, value in fields.items():
            if field == 'signature':
                print(f"    {field:<20}: {value}")
            elif field == 'flags':
                flag_desc = self._describe_zip_flags(value)
                print(f"    {field:<20}: {value} ({flag_desc})")
            elif field == 'compression_method':
                compress_type_str = self._get_compression_type_name(value)
                print(f"    {field:<20}: {value} ({compress_type_str})")
            elif field == 'last_mod_time':
                time_str = self._decode_dos_time(value)
                print(f"    {field:<20}: {value} ({time_str})")
            elif field == 'last_mod_date':
                date_str = self._decode_dos_date(value)
                print(f"    {field:<20}: {value} ({date_str})")
            elif field == 'external_file_attr':
                mode = value >> 16
                perm_str = self.format_mode(mode)
                print(f"    {field:<20}: {value} (Unix mode: {oct(mode)} {perm_str})")
            elif field == 'extra' and value:
                hex_value = ' '.join(f'{b:02x}' for b in value)
                print(f"    {field+'_hex':<20}: {hex_value}")
            elif field == 'extra_parsed':
                print(f"    {field:<20}:")
                for k, v in value.items():
                    if isinstance(v, dict):
                        print(f"      {k}:")
                        for sk, sv in v.items():
                            print(f"        {sk}: {sv}")
                    else:
                        print(f"      {k}: {v}")
            else:
                print(f"    {field:<20}: {value}")

    def _get_symlink_target(self, zip_file, entry):
        """Get the symlink target for a specific ZipInfo entry."""
        # Check if it's a symlink
        is_symlink = (entry.external_attr >> 16) & 0o170000 == 0o120000
        if not is_symlink:
            return None
        
        with zip_file.fp as fp:
            # Skip to the file data
            filename_length = len(entry.filename)
            extra_field_length = len(entry.extra)
            data_start = entry.header_offset + 30 + filename_length + extra_field_length
                        
            # Seek to data and read it
            fp.seek(data_start)
            target = fp.read(entry.file_size).decode('utf-8')
            fp.close()
            
            return target

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
                    'sticky': args.sticky if hasattr(args, 'sticky') else False
                })
                
                return self.replace(replace_args)
        else:
            archive = self._create_new_archive(args.file)
        
        try:
            # Process symlink
            if args.symlink:
                # For ZIP, we'll use the "0xA" file type flag to mark as symlink
                # This is compatible with InfoZIP and other modern ZIP tools
                info = zipfile.ZipInfo(args.path)
                
                # Set the external attributes to mark as a symlink
                # Unix symlink file mode (0120000) shifted left 16 bits
                symlink_mode = 0o120000
                if args.mode:
                    symlink_mode = (args.mode & 0o777) | 0o120000
                info.external_attr = symlink_mode << 16
                
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
                archive.writestr(info, args.hardlink)
            
            # Process regular file
            else:
                # For ZIP, we can control the basic info using ZipInfo
                info = zipfile.ZipInfo(args.path)
                
                # Set file mode if specified
                if args.mode:
                    # ZIP external_attr is mode << 16
                    info.external_attr = args.mode << 16
                else:
                    # Default to 0o644
                    info.external_attr = 0o744 << 16
                
                # Set modification time if specified
                if args.mtime:
                    # Convert to tuple for ZIP
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                # Set special bits if requested
                if args.setuid or args.setgid or args.sticky:
                    mode = 0o744  # default
                    if args.mode:
                        mode = args.mode
                    mode = self.apply_special_bits(mode, args)
                    info.external_attr = mode << 16
                
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
        with zipfile.ZipFile(args.file, "r") as zip_ref:
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
        with zipfile.ZipFile(args.file, "r") as zip_in:
            if args.path not in zip_in.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Extract the file content (if we're not converting to a link)
            content = zip_in.read(args.path) if not (args.symlink or args.hardlink) else None
            
            # Get the original info
            orig_info = zip_in.getinfo(args.path)
            
            # Get all other entries
            entries = [entry for entry in zip_in.infolist() 
                    if entry.filename != args.path]
            
            # Create a new ZIP file
            with zipfile.ZipFile(args.file + ".tmp", "w") as zip_out:
                # Copy all the other entries
                for entry in entries:
                    zip_out.writestr(entry, zip_in.read(entry.filename))
                
                # Create new info
                info = zipfile.ZipInfo(args.path)
                info.date_time = orig_info.date_time if args.mtime is None else datetime.fromtimestamp(args.mtime).timetuple()[:6]
                info.comment = orig_info.comment
                info.extra = orig_info.extra
                info.create_system = orig_info.create_system
                
                # Convert to symlink
                if args.symlink:
                    # Set the external attributes to mark as a symlink
                    # Unix symlink file mode (0120000) shifted left 16 bits
                    symlink_mode = 0o120000
                    if args.mode:
                        symlink_mode = (args.mode & 0o777) | 0o120000
                    info.external_attr = symlink_mode << 16
                    
                    # Set symlink target as the file content
                    zip_out.writestr(info, args.symlink)
                    
                    if args.verbose:
                        print(f"Converting {args.path} to symlink -> {args.symlink}")
                
                # Convert to hardlink - ZIP doesn't support hardlinks natively
                # We'll warn the user and create a file with the target as content
                elif args.hardlink:
                    print("Warning: ZIP format doesn't support hardlinks. "
                        "Creating a file with hardlink target as content.")
                    
                    # Apply regular file attributes
                    if args.mode:
                        info.external_attr = args.mode << 16
                    else:
                        info.external_attr = orig_info.external_attr
                    
                    # Set special bits if requested
                    if args.setuid or args.setgid or args.sticky:
                        mode = (orig_info.external_attr >> 16) & 0o777
                        if args.mode:
                            mode = args.mode
                        mode = self.apply_special_bits(mode, args)
                        info.external_attr = mode << 16
                    
                    # Add the file with hardlink target as content
                    zip_out.writestr(info, args.hardlink)
                
                # Regular attribute modification
                else:
                    # Apply changes
                    if args.mode:
                        info.external_attr = args.mode << 16
                    else:
                        info.external_attr = orig_info.external_attr
                    
                    # Set special bits if requested
                    if args.setuid or args.setgid or args.sticky:
                        # Get current mode from external_attr
                        mode = (orig_info.external_attr >> 16) & 0o777
                        if args.mode:
                            mode = args.mode
                        mode = self.apply_special_bits(mode, args)
                        info.external_attr = mode << 16
                    
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
            with zipfile.ZipFile(args.file, "r") as zip_in:
                # Get the list of entries
                entries = zip_in.infolist()

                # Recursive
                is_recursive = bool(args.recursive) if hasattr(args, 'recursive') else True
                
                # Check if the path exists in the archive
                paths_to_remove = []
                for entry in entries:
                    if entry.filename == args.path or (is_recursive and entry.filename.startswith(args.path.rstrip("/") + "/")):
                        paths_to_remove.append(entry.filename)
                
                if not paths_to_remove:
                    print(f"Error: {args.path} not found in the archive")
                    return
                
                # Get all entries except those we want to remove
                entries_to_keep = [entry for entry in entries 
                                if entry.filename not in paths_to_remove]
                
                # Create a new ZIP file
                with zipfile.ZipFile(args.file + ".tmp", "w") as zip_out:
                    # Copy all the other entries
                    for entry in entries_to_keep:
                        zip_out.writestr(entry, zip_in.read(entry.filename))
            
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
        
        except zipfile.BadZipFile:
            print(f"Error: {args.file} is not a valid ZIP file")

    def list(self, args):
        """List the contents of the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        try:
            with zipfile.ZipFile(args.file, "r") as zip_file:
                entries = zip_file.infolist()
                
                # Sort entries by name
                entries.sort(key=lambda e: e.filename)
                
                if not entries:
                    print(f"Archive {args.file} is empty")
                    return
                
                # Very verbose listing with all header information
                if hasattr(args, 'longlong') and args.longlong or args.long == 2:
                    print(f"Verbose header information for {args.file}:")
                    
                    # First find the End of Central Directory (EOCD) record
                    with open(args.file, 'rb') as raw_file:
                        # Go to the end of the file and search backward for the EOCD signature
                        raw_file.seek(0, 2)  # Seek to the end
                        file_size = raw_file.tell()
                        
                        # Find the EOCD record (search backwards from the end)
                        eocd_offset = None
                        max_search = min(file_size, 65536)  # ZIP spec allows comment up to 65535 bytes
                        for i in range(max_search):
                            raw_file.seek(file_size - 22 - i)  # EOCD is at least 22 bytes
                            if raw_file.read(4) == b'PK\x05\x06':  # EOCD signature
                                eocd_offset = file_size - 22 - i
                                break
                        
                        if eocd_offset is None:
                            print("Error: Could not find End of Central Directory record")
                            return
                        
                        # Read the EOCD record
                        raw_file.seek(eocd_offset)
                        eocd_data = raw_file.read(22)
                        eocd_fields = self._parse_eocd_record(eocd_data)
                        
                        # Get the offset to the start of the central directory
                        cd_offset = eocd_fields.get('cd_offset')
                        cd_entries = eocd_fields.get('cd_entries')
                        
                        if cd_offset is None or cd_entries is None:
                            print("Error: Invalid End of Central Directory record")
                            return
                        
                        # Find central directory headers
                        cd_headers = []
                        raw_file.seek(cd_offset)
                        
                        for _ in range(cd_entries):
                            pos = raw_file.tell()
                            if raw_file.read(4) != b'PK\x01\x02':  # CDH signature
                                print(f"Warning: Expected Central Directory Header at {pos}")
                                continue
                            
                            raw_file.seek(pos)
                            cdh_data = raw_file.read(46)  # Fixed part of CDH
                            cdh_fields = self._parse_central_directory_header(cdh_data)
                            
                            filename_length = cdh_fields.get('filename_length', 0)
                            extra_length = cdh_fields.get('extra_field_length', 0)
                            comment_length = cdh_fields.get('comment_length', 0)
                            
                            # Read variable-length fields
                            if filename_length > 0:
                                cdh_fields['filename'] = raw_file.read(filename_length).decode('utf-8', errors='replace')
                            
                            if extra_length > 0:
                                cdh_fields['extra'] = raw_file.read(extra_length)
                                # Parse the extra field
                                cdh_fields['extra_parsed'] = self._parse_extra_field(cdh_fields['extra'])
                            
                            if comment_length > 0:
                                cdh_fields['comment'] = raw_file.read(comment_length).decode('utf-8', errors='replace')
                            
                            # Store with offset and size
                            cd_headers.append({
                                'offset': pos,
                                'size': 46 + filename_length + extra_length + comment_length,
                                'fields': cdh_fields
                            })
                        
                        # Process each entry
                        for entry in entries:
                            print(f"\nFile: {entry.filename}")
                            print(f"{'-'*70}")
                            
                            # Find matching CDH by LFH offset
                            matching_cdh = None
                            for cdh in cd_headers:
                                if cdh['fields'].get('local_header_offset') == entry.header_offset:
                                    matching_cdh = cdh
                                    break
                            # If failed (for some reason), try fallback via filename
                            if matching_cdh == None:
                                for cdh in cd_headers:
                                    if cdh['fields'].get('filename') == entry.filename:
                                        matching_cdh = cdh
                                        break
                            # Couldnt find CDH entry match by LFH offset or filename
                            if matching_cdh == None:
                                print(f"Warning: failed to find central directory header for {entry.filename}")

                            # Display LFH (using header_offset which points to LFH)
                            raw_file.seek(entry.header_offset)
                            if raw_file.read(4) == b'PK\x03\x04':  # Verify LFH signature
                                raw_file.seek(entry.header_offset)
                                lfh_data = raw_file.read(30)  # Fixed part of LFH
                                lfh_fields = self._parse_local_file_header(lfh_data)
                                
                                filename_length = lfh_fields.get('filename_length', 0)
                                extra_length = lfh_fields.get('extra_field_length', 0)
                                
                                # Read variable-length fields
                                if filename_length > 0:
                                    lfh_fields['filename'] = raw_file.read(filename_length).decode('utf-8', errors='replace')
                                
                                if extra_length > 0:
                                    lfh_fields['extra'] = raw_file.read(extra_length)
                                    # Parse the extra field
                                    lfh_fields['extra_parsed'] = self._parse_extra_field(lfh_fields['extra'])
                                
                                print(f"\n  Local File Header (offset: {entry.header_offset}):")
                                self._display_zip_header_fields(lfh_fields)
                            
                            # Display matching CDH if found
                            if matching_cdh:
                                print(f"\n  Central Directory Header (offset: {matching_cdh['offset']}):")
                                self._display_zip_header_fields(matching_cdh['fields'])
                                
                                # Compare important fields between CDH and LFH
                                if 'fields' in matching_cdh and lfh_fields:
                                    print("\n  Header Field Comparison (CDH vs LFH):")
                                    fields_to_compare = [
                                        'version_needed', 'flags', 'compression_method',
                                        'last_mod_time', 'last_mod_date', 'crc_32',
                                        'compressed_size', 'uncompressed_size', 'filename'
                                    ]
                                    
                                    for field in fields_to_compare:
                                        if field in matching_cdh['fields'] and field in lfh_fields:
                                            match = matching_cdh['fields'][field] == lfh_fields[field]
                                            status = "MATCH" if match else "MISMATCH"
                                            print(f"    {field:<20}: {status} - CDH: {matching_cdh['fields'][field]}, LFH: {lfh_fields[field]}")
                            
                            print(f"{'-'*70}")
                elif args.long:
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
                        date_time = datetime(*entry.date_time)
                        date_str = date_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Get permissions 
                        # ZIP uses the high bits of external_attr for Unix permissions
                        mode = entry.external_attr >> 16
                        perm_str = self.format_mode(mode)
                        
                        # Check if it's a symlink by looking at file mode
                        is_symlink = mode & 0o170000 == 0o120000
                        name = entry.filename
                        
                        # If it's a symlink, try to get target
                        if is_symlink:
                            try:
                                target = self._get_symlink_target(zipfile.ZipFile(args.file, "r"), entry)
                                name = f"{entry.filename} -> {target}"
                            except Exception as e:
                                pass
                        
                        print(f"{perm_str} {entry.file_size:>10} {date_str:>20} {name}")
                    else:
                        print(f"{entry.filename}")
        
        except zipfile.BadZipFile:
            print(f"Error: {args.file} is not a valid ZIP file")

    def extract(self, args):
        """Extract files from the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Create output directory if it doesn't exist
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(args.file, "r") as zip_file:
                # Get list of entries to extract
                entries = zip_file.infolist()
                
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
                        symlink_target = zip_file.read(entry.filename).decode('utf-8')
                        
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
                            f.write(zip_file.read(entry.filename))
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
        
        except zipfile.BadZipFile:
            print(f"Error: {args.file} is not a valid ZIP file")
        except Exception as e:
            print(f"Error extracting {args.file}: {e}")