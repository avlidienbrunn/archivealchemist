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
                
                # Check if the path exists in the archive
                paths_to_remove = []
                for entry in entries:
                    if entry.filename == args.path or entry.filename.startswith(args.path.rstrip("/") + "/"):
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
                
                # Print header
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
                                target = zip_file.read(entry.filename).decode('utf-8')
                                name = f"{entry.filename} -> {target}"
                            except:
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