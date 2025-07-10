"""
Extended ZipFile class that builds on Python's standard zipfile module
but adds support for malformed/malicious ZIP files including:
- Orphaned Local File Headers (not referenced by Central Directory)
- Multiple Central Directory sections
- Conflicting information between LFH and CDH

Uses a single-pass scan and leverages zipfile's internal parsing functions.
"""

import zipfile
import struct
import os
import io
from collections import namedtuple

# Constants for ZIP structure sizes
LFH_FIXED_SIZE = 30      # Local File Header fixed part size
CDH_FIXED_SIZE = 46      # Central Directory Header fixed part size  
EOCD_FIXED_SIZE = 22     # End of Central Directory fixed part size

# Extended ZipInfo to track additional metadata
class ExtendedZipInfo(zipfile.ZipInfo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_offset = None       # Offset of Local File Header
        self.CRC = None                 # CRC
        self.lfh_offset = None          # Offset of Local File Header
        self.lfh_filename = None        # Filename from LFH (may differ from CDH)
        self.lfh_extra = None           # Extra field from LFH (may differ from CDH)
        self.cdh_filename = None        # Filename from CDH
        self.cdh_extra = None           # Extra field from CDH
        self.unicode_path = None        # Unicode path from extra field
        self.is_orphaned_lfh = False    # True if LFH exists but no CDH
        self.is_orphaned_cdh = False    # True if CDH exists but no LFH
        self.source_cd_index = 0        # Which central directory this came from
        self.data_offset = None         # Offset where file data starts

# Structure for PK signatures found during scan
PKSignature = namedtuple('PKSignature', ['offset', 'signature', 'sig_type'])

# Structure for parsed LFH
ParsedLFH = namedtuple('ParsedLFH', [
    'offset', 'zipinfo', 'data_offset', 'raw_extra', 'raw_fields'
])

# Structure for parsed CDH  
ParsedCDH = namedtuple('ParsedCDH', [
    'offset', 'zipinfo', 'lfh_offset', 'raw_extra', 'raw_fields'
])

# Structure for additional central directories
CentralDirectory = namedtuple('CentralDirectory', [
    'offset', 'size', 'entries_count', 'entries'
])


class ExtendedZipFile(zipfile.ZipFile):
    """Extended ZipFile with support for malformed ZIP structures."""
    
    def __init__(self, *args, **kwargs):
        # Extract orphaned_mode from kwargs before passing to parent
        self.orphaned_mode = kwargs.pop('orphaned_mode', False)
        
        self.pk_signatures = []         # All PK signatures found in file
        self.parsed_lfhs = []           # All LFH entries found
        self.parsed_cdhs = []           # All CDH entries found  
        self.central_directories = []   # All central directories found
        self.eocd_records = []          # All End of Central Directory records
        self.extended_infolist = []     # Extended ZipInfo objects
        self.orphaned_lfhs = []         # LFH entries not in any central directory
        
        # Call parent constructor
        super().__init__(*args, **kwargs)
        
        # If we successfully opened a file, scan for additional structures
        if hasattr(self, 'fp') and self.fp and hasattr(self.fp, 'read'):
            self._scan_file_once()
    
    def getinfo(self, name):
        """Return the instance of ZipInfo given 'name', including orphaned entries."""
        # First try the standard zipfile lookup
        if name in self.NameToInfo:
            return super().getinfo(name)
        
        # If not found in standard entries, check orphaned entries
        for entry in self.extended_infolist:
            if entry.filename == name:
                return entry
        
        # If still not found, raise KeyError
        raise KeyError(
            'There is no item named %r in the archive' % name)
    
    def namelist(self):
        """Return a list of file names in the archive, including orphaned entries."""
        # Get standard names
        names = super().namelist()
        
        # Add orphaned entry names
        for entry in self.extended_infolist:
            if entry.is_orphaned_lfh and entry.filename not in names:
                names.append(entry.filename)
        
        return names

    def _scan_file_once(self):
        """Single-pass scan of the entire ZIP file to find all PK signatures."""
        if not self.fp:
            return
            
        # Store current position
        original_pos = self.fp.tell()
        
        try:
            # TODO: stream read instead of reading all into ram?
            # Read entire file once
            self.fp.seek(0)
            file_data = self.fp.read()
            
            # Find all PK signatures in one pass
            self._find_all_pk_signatures(file_data)
            
            # Parse each signature using zipfile's internal functions
            self._parse_all_signatures(file_data)
            
            # Build extended info list
            self._build_extended_infolist()
            
        finally:
            # Restore file position
            self.fp.seek(original_pos)
    
    def _find_all_pk_signatures(self, file_data):
        """Find all PK signatures in the file data."""
        self.pk_signatures = []
        offset = 0
        
        while offset < len(file_data):
            # Look for any PK signature
            pos = file_data.find(b'PK', offset)
            if pos == -1:
                break
                
            # Check what type of PK signature this is
            if pos + 4 <= len(file_data):
                sig = file_data[pos:pos+4]
                sig_type = self._identify_pk_signature(sig)
                if sig_type:
                    self.pk_signatures.append(PKSignature(pos, sig, sig_type))
            
            offset = pos + 2  # Move past this PK
    
    def _identify_pk_signature(self, signature):
        """Identify the type of PK signature."""
        pk_types = {
            b'PK\x03\x04': 'LFH',      # Local File Header
            b'PK\x01\x02': 'CDH',      # Central Directory Header  
            b'PK\x05\x06': 'EOCD',     # End of Central Directory
            b'PK\x07\x08': 'DD',       # Data Descriptor
            b'PK\x06\x06': 'ZIP64_EOCD', # ZIP64 End of Central Directory
            b'PK\x06\x07': 'ZIP64_EOCDL', # ZIP64 End of Central Directory Locator
        }
        return pk_types.get(signature)
    
    def _parse_all_signatures(self, file_data):
        """Parse all found PK signatures using zipfile's parsing logic."""
        # TODO: do something with orphaned central directories?
        for pk_sig in self.pk_signatures:
            try:
                if pk_sig.sig_type == 'LFH':
                    parsed = self._parse_lfh_with_zipfile(file_data, pk_sig.offset)
                    if parsed:
                        self.parsed_lfhs.append(parsed)
                        
                elif pk_sig.sig_type == 'CDH':
                    parsed = self._parse_cdh_with_zipfile(file_data, pk_sig.offset)
                    if parsed:
                        self.parsed_cdhs.append(parsed)
                        
                elif pk_sig.sig_type == 'EOCD':
                    parsed = self._parse_eocd_with_zipfile(file_data, pk_sig.offset)
                    if parsed:
                        self.eocd_records.append(parsed)
                        
            except (struct.error, IndexError, UnicodeDecodeError):
                # Skip malformed entries
                continue
    
    def _parse_lfh_with_zipfile(self, file_data, offset):
        """Parse Local File Header using zipfile's logic."""
        if offset + LFH_FIXED_SIZE > len(file_data):
            return None
            
        try:
            header_data = file_data[offset:offset + LFH_FIXED_SIZE]
            
            # Verify signature
            if len(header_data) >= 4:
                sig = header_data[0:4]
                if sig != b'PK\x03\x04':
                    return None
            
            # Manual parsing for better control
            sig = struct.unpack('<4s', header_data[0:4])[0]
            version_needed = struct.unpack('<H', header_data[4:6])[0]
            flags = struct.unpack('<H', header_data[6:8])[0]
            compression_method = struct.unpack('<H', header_data[8:10])[0]
            last_mod_time = struct.unpack('<H', header_data[10:12])[0]
            last_mod_date = struct.unpack('<H', header_data[12:14])[0]
            crc32 = struct.unpack('<L', header_data[14:18])[0]
            compressed_size = struct.unpack('<L', header_data[18:22])[0]
            uncompressed_size = struct.unpack('<L', header_data[22:26])[0]
            filename_length = struct.unpack('<H', header_data[26:28])[0]
            extra_length = struct.unpack('<H', header_data[28:30])[0]
            
            # Store raw fields for display
            raw_fields = {
                'signature': sig,
                'version_needed': version_needed,
                'flags': flags,
                'compression_method': compression_method,
                'last_mod_time': last_mod_time,
                'last_mod_date': last_mod_date,
                'crc32': crc32,
                'compressed_size': compressed_size,
                'uncompressed_size': uncompressed_size,
                'filename_length': filename_length,
                'extra_length': extra_length
            }
            
            # Extract variable-length fields
            var_start = offset + LFH_FIXED_SIZE
            filename_end = var_start + filename_length
            extra_end = filename_end + extra_length
            
            if extra_end > len(file_data): # Corrupted LFH, extra end is out of bounds
                return None
                
            filename_bytes = file_data[var_start:filename_end]
            extra_bytes = file_data[filename_end:extra_end] if extra_length > 0 else b''
            
            # Decode filename using zipfile's logic
            try:
                if flags & 0x800:  # UTF-8 flag
                    filename = filename_bytes.decode('utf-8', errors='surrogateescape')
                else:
                    filename = filename_bytes.decode('cp437', errors='surrogateescape')
            except UnicodeDecodeError:
                filename = filename_bytes.decode('utf-8', errors='surrogateescape')
            
            # Create ZipInfo object
            zipinfo = zipfile.ZipInfo(filename)
            zipinfo.compress_type = compression_method
            zipinfo.CRC = crc32
            zipinfo.compress_size = compressed_size
            zipinfo.file_size = uncompressed_size
            zipinfo.header_offset = offset
            zipinfo.extra = extra_bytes
            
            # Set date_time using zipfile's logic
            zipinfo.date_time = self._dos_date_time_to_tuple(last_mod_date, last_mod_time)
            
            # Calculate data offset
            data_offset = filename_end + extra_length
            
            return ParsedLFH(
                offset=offset,
                zipinfo=zipinfo,
                data_offset=data_offset,
                raw_extra=extra_bytes,
                raw_fields=raw_fields
            )
            
        except (struct.error, UnicodeDecodeError):
            return None
    
    def _parse_cdh_with_zipfile(self, file_data, offset):
        """Parse Central Directory Header using zipfile's logic."""
        if offset + CDH_FIXED_SIZE > len(file_data):
            return None
            
        try:
            header_data = file_data[offset:offset + CDH_FIXED_SIZE]
            
            # Verify signature first
            sig = struct.unpack('<4s', header_data[0:4])[0]
            if sig != b'PK\x01\x02':
                return None
            
            # Manual parsing for better control (like we do in LFH)
            version_made_by = struct.unpack('<H', header_data[4:6])[0]
            version_needed = struct.unpack('<H', header_data[6:8])[0]
            flags = struct.unpack('<H', header_data[8:10])[0]
            compression_method = struct.unpack('<H', header_data[10:12])[0]
            last_mod_time = struct.unpack('<H', header_data[12:14])[0]
            last_mod_date = struct.unpack('<H', header_data[14:16])[0]
            crc32 = struct.unpack('<L', header_data[16:20])[0]
            compressed_size = struct.unpack('<L', header_data[20:24])[0]
            uncompressed_size = struct.unpack('<L', header_data[24:28])[0]
            filename_length = struct.unpack('<H', header_data[28:30])[0]
            extra_length = struct.unpack('<H', header_data[30:32])[0]
            comment_length = struct.unpack('<H', header_data[32:34])[0]
            disk_start = struct.unpack('<H', header_data[34:36])[0]
            internal_attr = struct.unpack('<H', header_data[36:38])[0]
            external_attr = struct.unpack('<L', header_data[38:42])[0]
            lfh_offset = struct.unpack('<L', header_data[42:46])[0]
            
            # Store raw fields for display (similar to LFH)
            raw_fields = {
                'signature': sig,
                'version_made_by': version_made_by,
                'version_needed': version_needed,
                'flags': flags,
                'compression_method': compression_method,
                'last_mod_time': last_mod_time,
                'last_mod_date': last_mod_date,
                'crc32': crc32,
                'compressed_size': compressed_size,
                'uncompressed_size': uncompressed_size,
                'filename_length': filename_length,
                'extra_length': extra_length,
                'comment_length': comment_length,
                'disk_start': disk_start,
                'internal_attr': internal_attr,
                'external_attr': external_attr,
                'lfh_offset': lfh_offset
            }
            
            # Extract variable-length fields
            var_start = offset + CDH_FIXED_SIZE
            filename_end = var_start + filename_length
            extra_end = filename_end + extra_length
            comment_end = extra_end + comment_length
            
            if comment_end > len(file_data): # Corrupted CDH, comment end is out of bounds
                return None
                
            filename_bytes = file_data[var_start:filename_end]
            extra_bytes = file_data[filename_end:extra_end]
            comment_bytes = file_data[extra_end:comment_end]
            
            # Store the variable-length data in raw_fields too
            raw_fields['filename'] = filename_bytes
            raw_fields['extra'] = extra_bytes
            raw_fields['comment'] = comment_bytes
            
            # Decode filename using zipfile's logic
            try:
                if flags & 0x800:  # UTF-8 flag
                    filename = filename_bytes.decode('utf-8', errors='surrogateescape')
                else:
                    filename = filename_bytes.decode('cp437', errors='surrogateescape')
            except UnicodeDecodeError:
                filename = filename_bytes.decode('utf-8', errors='surrogateescape')
            
            # Create ZipInfo object
            zipinfo = zipfile.ZipInfo(filename)
            zipinfo.compress_type = compression_method
            zipinfo.CRC = crc32
            zipinfo.compress_size = compressed_size
            zipinfo.file_size = uncompressed_size
            zipinfo.header_offset = lfh_offset
            zipinfo.extra = extra_bytes
            zipinfo.external_attr = external_attr
            
            if len(comment_bytes) > 0:
                zipinfo.comment = comment_bytes
            
            # Set date_time using zipfile's logic
            zipinfo.date_time = self._dos_date_time_to_tuple(last_mod_date, last_mod_time)
            
            return ParsedCDH(
                offset=offset,
                zipinfo=zipinfo,
                lfh_offset=lfh_offset,
                raw_extra=extra_bytes,
                raw_fields=raw_fields
            )
            
        except (struct.error, UnicodeDecodeError):
            return None
    
    def _parse_eocd_with_zipfile(self, file_data, offset):
        """Parse End of Central Directory using zipfile's logic."""
        if offset + EOCD_FIXED_SIZE > len(file_data):
            return None
            
        try:
            # Use zipfile's struct format for EOCD
            header_data = file_data[offset:offset + EOCD_FIXED_SIZE]
            header = struct.unpack(zipfile.structEndArchive, header_data)
            
            signature = header[0]
            if signature != zipfile.stringEndArchive:  # b'PK\x05\x06'
                return None
                
            disk_number = header[1]
            cd_disk = header[2]
            disk_entries = header[3]
            total_entries = header[4]
            cd_size = header[5]
            cd_offset = header[6]
            comment_length = header[7]
            
            # Extract comment if present
            comment = b''
            if comment_length > 0:
                comment_end = offset + EOCD_FIXED_SIZE + comment_length
                if comment_end <= len(file_data):
                    comment = file_data[offset + EOCD_FIXED_SIZE:comment_end]
            
            return {
                'offset': offset,
                'cd_offset': cd_offset,
                'cd_size': cd_size,
                'total_entries': total_entries,
                'comment': comment
            }
            
        except struct.error:
            return None
    
    def _build_extended_infolist(self):
        """Build extended info list combining standard and orphaned entries."""
        self.extended_infolist = []
        self.orphaned_lfhs = []
        
        # Get offsets of all LFHs referenced by standard central directory
        standard_lfh_offsets = set()
        for info in self.infolist():
            if hasattr(info, 'header_offset'):
                standard_lfh_offsets.add(info.header_offset)
        
        # Create extended entries for standard zipfile entries
        for info in self.infolist():
            extended = self._create_extended_zipinfo_from_standard(info)
            self.extended_infolist.append(extended)
        
        # Find orphaned LFH entries (not referenced by standard zipfile)
        # Only include orphaned entries if orphaned_mode is enabled
        if self.orphaned_mode:
            for lfh in self.parsed_lfhs:
                if lfh.offset not in standard_lfh_offsets:
                    # This is an orphaned LFH
                    extended = self._create_extended_zipinfo_from_lfh(lfh)
                    extended.is_orphaned_lfh = True
                    extended.is_orphaned_cdh = True
                    
                    # Try to find matching CDH for this orphaned LFH
                    matching_cdh = self._find_matching_cdh_for_lfh(lfh)
                    if matching_cdh:
                        # Merge CDH information into the extended info
                        extended = self._merge_cdh_into_extended_info(extended, matching_cdh)
                        extended.is_orphaned_cdh = False
                    
                    self.extended_infolist.append(extended)
                    self.orphaned_lfhs.append(lfh)

    def _find_matching_cdh_for_lfh(self, lfh):
        """Find a CDH entry that points to this LFH offset."""
        # TODO: What if multiple CDH reference the same LFH?
        for cdh in self.parsed_cdhs:
            if cdh.lfh_offset == lfh.offset:
                return cdh
        return None

    def _merge_cdh_into_extended_info(self, extended_info, cdh):
        """Merge CDH information into an ExtendedZipInfo object."""
        # Set CDH-specific metadata
        extended_info.cdh_filename = cdh.zipinfo.filename
        extended_info.cdh_extra = cdh.raw_extra
        
        # Set CDH index
        extended_info.source_cd_index = self.parsed_cdhs.index(cdh) if cdh in self.parsed_cdhs else -1
        
        # Update external attributes (permissions) from CDH
        if hasattr(cdh.zipinfo, 'external_attr'):
            extended_info.external_attr = cdh.zipinfo.external_attr
        
        # Update comment from CDH (LFH doesn't have comments)
        if hasattr(cdh.zipinfo, 'comment'):
            extended_info.comment = cdh.zipinfo.comment
        
        # If CDH has extra field data, merge it (prioritizing CDH for conflicts)
        if cdh.raw_extra:
            extended_info.extra = cdh.raw_extra
            # Re-extract Unicode path with the new extra data
            extended_info.unicode_path = self._extract_unicode_path(extended_info)
        
        return extended_info
    
    def _create_extended_zipinfo_from_standard(self, info):
        """Create ExtendedZipInfo from standard ZipInfo."""
        extended = ExtendedZipInfo(info.filename)
        
        # Copy all attributes from original ZipInfo
        for attr in dir(info):
            if not attr.startswith('_') and hasattr(extended, attr):
                try:
                    setattr(extended, attr, getattr(info, attr))
                except AttributeError:
                    pass
        
        # Add extended metadata
        extended.cdh_filename = info.filename
        extended.source_cd_index = 0  # Main central directory
        
        # Find corresponding LFH for comparison
        if hasattr(info, 'header_offset'):
            lfh = self._find_lfh_by_offset(info.header_offset)
            if lfh:
                extended.lfh_filename = lfh.zipinfo.filename
                extended.lfh_extra = lfh.raw_extra
                extended.lfh_offset = lfh.offset
                extended.data_offset = lfh.data_offset
        
        # Extract Unicode path from available sources
        extended.unicode_path = self._extract_unicode_path(extended)
        
        # Standard entries are never orphaned
        extended.is_orphaned_lfh = False
        extended.is_orphaned_cdh = False

        return extended
    
    def _create_extended_zipinfo_from_lfh(self, lfh):
        """Create ExtendedZipInfo from orphaned LFH."""
        extended = ExtendedZipInfo(lfh.zipinfo.filename)
        
        # Copy attributes from LFH's ZipInfo
        for attr in dir(lfh.zipinfo):
            if not attr.startswith('_') and hasattr(extended, attr):
                try:
                    setattr(extended, attr, getattr(lfh.zipinfo, attr))
                except AttributeError:
                    pass
        
        # Set extended metadata
        extended.lfh_filename = lfh.zipinfo.filename
        extended.lfh_extra = lfh.raw_extra
        extended.lfh_offset = lfh.offset
        extended.data_offset = lfh.data_offset
        
        # Ensure critical fields are set correctly for orphaned LFHs
        extended.header_offset = lfh.offset  # Where the LFH is located
        if hasattr(lfh.zipinfo, 'CRC'):
            extended.CRC = lfh.zipinfo.CRC  # CRC32 from LFH
        
        # Extract Unicode path from LFH extra field
        extended.unicode_path = self._extract_unicode_path(extended)
        
        return extended
    
    def _find_lfh_by_offset(self, offset):
        """Find LFH entry by offset."""
        for lfh in self.parsed_lfhs:
            if lfh.offset == offset:
                return lfh
        return None
    
    def get_extended_infolist(self):
        """Get the extended info list with all entries including orphaned ones."""
        return self.extended_infolist
    
    def get_display_name(self, extended_info):
        """
        Generate display name from unicode_path / cdh_name / lfh_name
        """
        parts = []
        
        unicode_name = self._extract_unicode_path(extended_info)
        cdh_name = getattr(extended_info, 'cdh_filename', None)
        lfh_name = getattr(extended_info, 'lfh_filename', None)
        
        if unicode_name: 
            parts.append(f"{unicode_name} (U)")
        if cdh_name: 
            parts.append(f"{cdh_name} (C)")
        if lfh_name: 
            parts.append(f"{lfh_name} (L)")
        
        if unicode_name:
            if unicode_name == cdh_name and unicode_name == lfh_name:
                parts = [unicode_name]
        else:
            if cdh_name == lfh_name:
                parts = [cdh_name]

        
        return ' '.join(parts) if parts else extended_info.filename
    
    def _extract_unicode_path(self, extended_info):
        """Extract Unicode path from extra field if present."""
        # Check both LFH and CDH extra fields
        for extra in [getattr(extended_info, 'lfh_extra', None), 
                     getattr(extended_info, 'extra', None)]:
            if not extra:
                continue
                
            # Look for Unicode Path extra field (0x7075)
            pos = 0
            while pos + 4 <= len(extra):
                try:
                    header_id = struct.unpack('<H', extra[pos:pos+2])[0]
                    data_size = struct.unpack('<H', extra[pos+2:pos+4])[0]
                    
                    if header_id == 0x7075 and pos + 4 + data_size <= len(extra):
                        # Unicode Path field found
                        data = extra[pos+4:pos+4+data_size]
                        if len(data) >= 5:  # version(1) + crc32(4) + path
                            unicode_path = data[5:]  # Skip version and CRC32
                            try:
                                return unicode_path.decode('utf-8', errors='surrogateescape')
                            except UnicodeDecodeError:
                                pass
                    
                    pos += 4 + data_size
                except (struct.error, IndexError):
                    break
        
        return None


    # Helper function for DOS date/time conversion
    def _dos_date_time_to_tuple(self, date, time):
        """Convert DOS date/time to Python datetime tuple."""
        d = date
        t = time
        year = ((d >> 9) & 0x7f) + 1980
        month = (d >> 5) & 0x0f
        day = d & 0x1f
        hour = (t >> 11) & 0x1f
        minute = (t >> 5) & 0x3f
        second = (t & 0x1f) * 2
        return (year, month, day, hour, minute, second)