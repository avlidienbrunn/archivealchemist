"""
Handler for ZIP archive operations.
Implements the BaseArchiveHandler interface for ZIP archives.
"""

import os
import zipfile
from datetime import datetime
from handlers.base_handler import BaseArchiveHandler


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
    
    def add(self, args):
        """Add a file or symlink to the ZIP archive."""
        # Create archive or open existing
        if os.path.exists(args.file):
            archive = self._open_existing_archive(args.file)
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
                    info.external_attr = 0o644 << 16
                
                # Set modification time if specified
                if args.mtime:
                    # Convert to tuple for ZIP
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                # Set special bits if requested
                if args.setuid or args.setgid or args.sticky:
                    mode = 0o644  # default
                    if args.mode:
                        mode = args.mode
                    mode = self.apply_special_bits(mode, args)
                    info.external_attr = mode << 16
                
                # Add the file to the archive
                content = args.content if args.content else ""
                archive.writestr(info, content)
                
                if args.verbose:
                    print(f"Added {args.path} to {args.file}")
                
        finally:
            archive.close()
    
    def replace(self, args):
        """Replace a file in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # For ZIP, we need to extract, modify, and rewrite the archive
        with zipfile.ZipFile(args.file, "r") as zip_in:
            # Check if the file exists
            if args.path not in zip_in.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Get the list of entries, excluding the one we want to replace
            entries = [entry for entry in zip_in.infolist() 
                    if entry.filename != args.path]
            
            # Create a new ZIP file
            with zipfile.ZipFile(args.file + ".tmp", "w") as zip_out:
                # Copy all the other entries
                for entry in entries:
                    zip_out.writestr(entry, zip_in.read(entry.filename))
                
                # Add the replaced entry
                zip_out.writestr(args.path, args.content)
        
        # Replace the original file
        os.remove(args.file)
        os.rename(args.file + ".tmp", args.file)
        
        if args.verbose:
            print(f"Replaced {args.path} in {args.file}")
    
    def append(self, args):
        """Append content to a file in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Extract the file, append content, and replace it
        with zipfile.ZipFile(args.file, "r") as zip_ref:
            if args.path not in zip_ref.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Extract the file content
            content = zip_ref.read(args.path).decode("utf-8")
            
            # Append content
            new_content = content + args.content
            
            # Create temporary args for replace
            replace_args = type('Args', (), {
                'file': args.file,
                'path': args.path,
                'content': new_content,
                'verbose': args.verbose
            })
            
            # Call replace with the new content
            self.replace(replace_args)
    
    def modify(self, args):
        """Modify file attributes in the ZIP archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # For ZIP, we need to extract, modify, and rewrite
        with zipfile.ZipFile(args.file, "r") as zip_in:
            if args.path not in zip_in.namelist():
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Extract the file content
            content = zip_in.read(args.path)
            
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
                
                # Create new info with modified attributes
                info = zipfile.ZipInfo(args.path)
                info.date_time = orig_info.date_time
                info.comment = orig_info.comment
                info.extra = orig_info.extra
                info.create_system = orig_info.create_system
                
                # Apply changes
                if args.mode:
                    info.external_attr = args.mode << 16
                else:
                    info.external_attr = orig_info.external_attr
                
                if args.mtime:
                    dt = datetime.fromtimestamp(args.mtime)
                    info.date_time = (dt.year, dt.month, dt.day, 
                                    dt.hour, dt.minute, dt.second)
                
                # Set special bits if requested
                if args.setuid or args.setgid or args.sticky:
                    # Get current mode from external_attr
                    mode = (orig_info.external_attr >> 16) & 0o777
                    if args.mode:
                        mode = args.mode
                    mode = self.apply_special_bits(mode, args)
                    info.external_attr = mode << 16
                
                # Add the modified entry
                zip_out.writestr(info, content)
        
        # Replace the original file
        os.remove(args.file)
        os.rename(args.file + ".tmp", args.file)
        
        if args.verbose:
            print(f"Modified attributes of {args.path} in {args.file}")