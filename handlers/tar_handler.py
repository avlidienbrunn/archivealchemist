"""
Handler for TAR archive operations.
Implements the BaseArchiveHandler interface for TAR archives.
"""

import io
import os
import tarfile
import tempfile
from datetime import datetime
from handlers.base_handler import BaseArchiveHandler


class TarHandler(BaseArchiveHandler):
    """Handler for TAR archives."""
    
    def __init__(self, compressed=False):
        """Initialize the TAR handler.
        
        Args:
            compressed: Whether to use gzip compression.
        """
        self.compressed = compressed
    
    def _get_mode(self, operation, binary=False):
        """Get the mode string for tarfile operations.
        
        Args:
            operation: The operation to perform (r, w, a).
            binary: Whether to open in binary mode.
        
        Returns:
            The mode string for tarfile.open().
        """
        if self.compressed:
            if operation == "r":
                return "r:gz"
            elif operation == "w":
                return "w:gz"
            elif operation == "a":
                # Note: appending to compressed archives is problematic
                # We'll need to rewrite the entire archive
                return "w:gz"
        else:
            if binary and operation != "r":
                return f"{operation}b"
            return operation
    
    def _create_new_archive(self, file_path):
        """Create a new TAR archive."""
        mode = self._get_mode("w")
        return tarfile.open(file_path, mode)
    
    def _open_existing_archive(self, file_path, mode="a"):
        """Open an existing TAR archive."""
        tar_mode = self._get_mode(mode)
        return tarfile.open(file_path, tar_mode)
    
    def add(self, args):
        """Add a file or symlink to the TAR archive."""
        # Create archive or open existing
        if os.path.exists(args.file):
            # For compressed archives, we need to rewrite the entire archive
            needs_rewrite = True
            read_archive = self._open_existing_archive(args.file, "r")
            temp_file = args.file + ".tmp"
            write_archive = self._create_new_archive(temp_file)
        else:
            # New archive
            archive = self._create_new_archive(args.file)
            needs_rewrite = False
        
        try:
            if needs_rewrite:
                # Copy all existing entries
                for entry in read_archive.getmembers():
                    # --content-directory should replace entry if it already exists
                    file_exists = args.path == entry.name
                    if file_exists and getattr(args, 'content_directory', None) is not None:
                        continue
                    if entry.isfile():
                        file_data = read_archive.extractfile(entry)
                        write_archive.addfile(entry, file_data)
                    else:
                        write_archive.addfile(entry)
                
                # Use the write archive as our working archive
                archive = write_archive
            
            # Process symlink
            if args.symlink:
                # Create a tarinfo for the symlink
                tarinfo = tarfile.TarInfo(args.path)
                tarinfo.type = tarfile.SYMTYPE
                tarinfo.linkname = args.symlink
                tarinfo.size = 0  # Symlinks don't have content
                tarinfo.mode = 0o744
                
                # Apply attributes if specified
                if args.mode:
                    tarinfo.mode = args.mode
                if args.uid is not None:
                    tarinfo.uid = args.uid
                if args.gid is not None:
                    tarinfo.gid = args.gid
                if args.mtime is not None:
                    tarinfo.mtime = args.mtime
                
                # Apply special bits
                if args.setuid or args.setgid or args.sticky:
                    mode = tarinfo.mode
                    mode = self.apply_special_bits(mode, args)
                    tarinfo.mode = mode
                
                # Add the symlink to the archive
                archive.addfile(tarinfo)
                
                if args.verbose:
                    print(f"Added symlink {args.path} -> {args.symlink} to {args.file}")
            
            # Process hardlink
            elif args.hardlink:
                # Create a tarinfo for the hardlink
                tarinfo = tarfile.TarInfo(args.path)
                tarinfo.type = tarfile.LNKTYPE
                tarinfo.linkname = args.hardlink
                tarinfo.size = 0  # Hardlinks don't have content
                tarinfo.mode = 0o744
                
                # Apply attributes if specified
                if args.mode:
                    tarinfo.mode = args.mode
                if args.uid is not None:
                    tarinfo.uid = args.uid
                if args.gid is not None:
                    tarinfo.gid = args.gid
                if args.mtime is not None:
                    tarinfo.mtime = args.mtime
                
                # Apply special bits
                if args.setuid or args.setgid or args.sticky:
                    mode = tarinfo.mode
                    mode = self.apply_special_bits(mode, args)
                    tarinfo.mode = mode
                
                # Add the hardlink to the archive
                archive.addfile(tarinfo)
                
                if args.verbose:
                    print(f"Added hardlink {args.path} -> {args.hardlink} to {args.file}")
            
            # Process regular file
            else:
                # Get content from either --content or --content-file
                try:
                    content_bytes = self.get_content(args)
                except (ValueError, FileNotFoundError) as e:
                    print(f"Error: {e}")
                    return
                
                # Create a tarinfo for the file
                tarinfo = tarfile.TarInfo(args.path)
                tarinfo.size = len(content_bytes)
                tarinfo.mode = 0o744
                
                # Apply attributes if specified
                if args.mode is not None:
                    tarinfo.mode = args.mode
                if args.uid is not None:
                    tarinfo.uid = args.uid
                if args.gid is not None:
                    tarinfo.gid = args.gid
                if args.mtime is not None:
                    tarinfo.mtime = args.mtime
                
                # Apply special bits
                if args.setuid or args.setgid or args.sticky:
                    mode = tarinfo.mode
                    mode = self.apply_special_bits(mode, args)
                    tarinfo.mode = mode
                
                # Add the file to the archive with content
                archive.addfile(tarinfo, io.BytesIO(content_bytes))
                
                if args.verbose:
                    if args.content_file:
                        print(f"Added {args.path} with content from {args.content_file} to {args.file}")
                    else:
                        print(f"Added {args.path} to {args.file}")
        finally:
            archive.close()
            if needs_rewrite:
                read_archive.close()
                # Replace the original file
                os.remove(args.file)
                os.rename(temp_file, args.file)

    # Update the replace method in TarHandler
    def replace(self, args):
        """Replace a file in the TAR archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Get content from either --content or --content-file
        try:
            content = self.get_content(args)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}")
            return
        
        # If neither content nor content-file is specified, show an error
        if not args.content and not args.content_file and getattr(args, 'require_content', True):
            print("Error: Either --content or --content-file must be specified")
            return
        
        # For TAR, we need to extract, modify, and rewrite the archive
        # Open the existing archive
        read_mode = self._get_mode("r")
        with tarfile.open(args.file, read_mode) as tar_in:
            # Check if the file exists
            member_names = [m.name for m in tar_in.getmembers()]
            if args.path not in member_names:
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Get the original member
            orig_member = next(m for m in tar_in.getmembers() if m.name == args.path)
            
            # Get all other entries
            entries = [entry for entry in tar_in.getmembers()
                    if entry.name != args.path]
            
            # Create a new TAR file
            write_mode = self._get_mode("w")
            with tarfile.open(args.file + ".tmp", write_mode) as tar_out:
                # Copy all the other entries
                for entry in entries:
                    if entry.isfile():
                        file_data = tar_in.extractfile(entry)
                        tar_out.addfile(entry, file_data)
                    else:
                        tar_out.addfile(entry)
                
                # Create a new tarinfo with the same attributes
                tarinfo = tarfile.TarInfo(args.path)
                tarinfo.size = len(content)
                tarinfo.mode = orig_member.mode
                tarinfo.type = orig_member.type
                tarinfo.linkname = orig_member.linkname
                tarinfo.uid = orig_member.uid
                tarinfo.gid = orig_member.gid
                tarinfo.uname = orig_member.uname
                tarinfo.gname = orig_member.gname
                tarinfo.mtime = orig_member.mtime
                
                # Add the replaced file with new content
                tar_out.addfile(tarinfo, io.BytesIO(content))
        
        # Replace the original file
        os.remove(args.file)
        os.rename(args.file + ".tmp", args.file)
        
        if args.verbose:
            if args.content_file:
                print(f"Replaced {args.path} with content from {args.content_file} in {args.file}")
            else:
                print(f"Replaced {args.path} in {args.file}")

    # Update the append method in TarHandler
    def append(self, args):
        """Append content to a file in the TAR archive."""
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
        if not args.content and not args.content_file and getattr(args, 'require_content', True):
            print("Error: Either --content or --content-file must be specified")
            return
        
        # Extract the file, append content, and replace it
        read_mode = self._get_mode("r")
        with tarfile.open(args.file, read_mode) as tar_ref:
            member_names = [m.name for m in tar_ref.getmembers()]
            if args.path not in member_names:
                print(f"Error: {args.path} not found in the archive")
                return
            
            # Get the file member
            member = next(m for m in tar_ref.getmembers() if m.name == args.path)
            
            # Check if it's a regular file
            if not member.isfile():
                print(f"Error: {args.path} is not a regular file")
                return
            
            # Extract the file content
            existing_content = tar_ref.extractfile(args.path).read()
            
            # Append content
            new_content = existing_content + append_content
            
            # Create temporary args for replace
            replace_args = type('Args', (), {
                'file': args.file,
                'path': args.path,
                'content': new_content,
                'content_file': None,
                'verbose': args.verbose,
                'require_content': False
            })
            
            # Call replace with the new content
            self.replace(replace_args)
        
        if args.verbose:
            if args.content_file:
                print(f"Appended content from {args.content_file} to {args.path} in {args.file}")
            else:
                print(f"Appended to {args.path} in {args.file}")
    
    def modify(self, args):
        """Modify file attributes in the TAR archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Check for both symlink and hardlink options
        if args.symlink and args.hardlink:
            print("Error: Cannot specify both --symlink and --hardlink")
            return

        # For TAR, we need to extract, modify, and rewrite the archive
        with tempfile.TemporaryDirectory() as temp_dir:
            # Open the existing archive
            read_mode = self._get_mode("r")
            with tarfile.open(args.file, read_mode) as tar_in:
                # Check if the file exists
                member_names = [m.name for m in tar_in.getmembers()]
                if args.path not in member_names:
                    print(f"Error: {args.path} not found in the archive")
                    return
                
                # Get the original member
                orig_member = next(m for m in tar_in.getmembers() if m.name == args.path)
                
                # Get all other entries
                entries = [entry for entry in tar_in.getmembers() if entry.name != args.path]
                
                # Create a new TAR file
                write_mode = self._get_mode("w")
                with tarfile.open(args.file + ".tmp", write_mode) as tar_out:
                    # Copy all the other entries
                    for entry in entries:
                        if entry.isfile():
                            file_data = tar_in.extractfile(entry)
                            tar_out.addfile(entry, file_data)
                        else:
                            tar_out.addfile(entry)
                    
                    # Create a new tarinfo based on the modification type
                    tarinfo = tarfile.TarInfo(args.path)
                    
                    # Handle conversion to symlink
                    if args.symlink:
                        tarinfo.type = tarfile.SYMTYPE
                        tarinfo.linkname = args.symlink
                        tarinfo.size = 0  # Symlinks don't have content
                        
                        if args.verbose:
                            print(f"Converting {args.path} to symlink -> {args.symlink}")
                    
                    # Handle conversion to hardlink
                    elif args.hardlink:
                        tarinfo.type = tarfile.LNKTYPE
                        tarinfo.linkname = args.hardlink
                        tarinfo.size = 0  # Hardlinks don't have content
                        
                        if args.verbose:
                            print(f"Converting {args.path} to hardlink -> {args.hardlink}")
                    
                    # Normal attribute modification
                    else:
                        tarinfo.size = orig_member.size
                        tarinfo.type = orig_member.type
                        tarinfo.linkname = orig_member.linkname
                        
                        # Add the file data if it's a regular file
                        if orig_member.isfile():
                            file_data = tar_in.extractfile(orig_member)
                    
                    # Set common attributes
                    tarinfo.uid = orig_member.uid if args.uid is None else args.uid
                    tarinfo.gid = orig_member.gid if args.gid is None else args.gid
                    tarinfo.uname = orig_member.uname
                    tarinfo.gname = orig_member.gname
                    tarinfo.mtime = orig_member.mtime if args.mtime is None else args.mtime
                    
                    # Set mode and special bits
                    mode = orig_member.mode
                    if args.mode is not None:
                        mode = args.mode
                    
                    # Apply special bits if requested
                    mode = self.apply_special_bits(mode, args)
                    tarinfo.mode = mode
                    
                    # Add the modified file to the archive
                    if not args.symlink and not args.hardlink and orig_member.isfile():
                        tar_out.addfile(tarinfo, file_data)
                    else:
                        tar_out.addfile(tarinfo)
            
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
        """Remove a file from the TAR archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Open the existing archive
        try:
            read_mode = self._get_mode("r")
            with tarfile.open(args.file, read_mode) as tar_in:
                # Check if the path exists in the archive
                member_names = [m.name for m in tar_in.getmembers()]
                
                # Find all paths to remove (including directories)
                paths_to_remove = []
                for name in member_names:
                    if name == args.path or name.startswith(args.path + "/"):
                        paths_to_remove.append(name)
                
                if not paths_to_remove:
                    print(f"Error: {args.path} not found in the archive")
                    return
                
                # Get all entries except those we want to remove
                entries_to_keep = [entry for entry in tar_in.getmembers()
                                if entry.name not in paths_to_remove]
                
                # Create a new TAR file
                write_mode = self._get_mode("w")
                with tarfile.open(args.file + ".tmp", write_mode) as tar_out:
                    # Copy all the entries we want to keep
                    for entry in entries_to_keep:
                        if entry.isfile():
                            file_data = tar_in.extractfile(entry)
                            tar_out.addfile(entry, file_data)
                        else:
                            tar_out.addfile(entry)
            
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
        
        except tarfile.ReadError:
            print(f"Error: {args.file} is not a valid TAR file")

    def list(self, args):
        """List the contents of the TAR archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        try:
            read_mode = self._get_mode("r")
            with tarfile.open(args.file, read_mode) as tar_file:
                members = tar_file.getmembers()
                
                # Sort members by name
                members.sort(key=lambda m: m.name)
                
                if not members:
                    print(f"Archive {args.file} is empty")
                    return
                
                # Print header
                if args.long:
                    print(f"{'Permissions':<12} {'Owner/Group':<15} {'Size':>10} {'Modified':>20} {'Name'}")
                    print(f"{'-'*12} {'-'*15} {'-'*10} {'-'*20} {'-'*30}")
                else:
                    print(f"Contents of {args.file}:")
                
                # Print members
                for member in members:
                    # Skip directories for simple listing
                    if not args.long and member.isdir():
                        continue
                    
                    if args.long:
                        # Format date and time
                        date_time = datetime.fromtimestamp(member.mtime)
                        date_str = date_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Format permissions
                        perm_str = self.format_mode(member.mode)
                        
                        # Format owner/group
                        if member.uname and member.gname:
                            owner_str = f"{member.uname}/{member.gname}"
                        else:
                            owner_str = f"{member.uid}/{member.gid}"
                        
                        # Handle symlinks
                        name = member.name
                        if member.issym():
                            name = f"{member.name} -> {member.linkname}"
                        elif member.islnk():
                            name = f"{member.name} link to {member.linkname}"
                        
                        print(f"{perm_str} {owner_str:<15} {member.size:>10} {date_str:>20} {name}")
                    else:
                        print(f"{member.name}")
        
        except tarfile.ReadError:
            print(f"Error: {args.file} is not a valid TAR file")

    def extract(self, args):
        """Extract files from the TAR archive."""
        if not os.path.exists(args.file):
            print(f"Error: Archive {args.file} does not exist")
            return
        
        # Create output directory if it doesn't exist
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir, exist_ok=True)
        
        try:
            read_mode = self._get_mode("r")
            with tarfile.open(args.file, read_mode) as tar_file:
                # Get list of members to extract
                members = tar_file.getmembers()
                
                # Filter members if a specific path is specified
                if args.path:
                    # Keep members that match the path or are under the path directory
                    members = [member for member in members if
                            member.name == args.path or
                            member.name.startswith(args.path + "/")]
                    
                    if not members:
                        print(f"Error: Path '{args.path}' not found in the archive")
                        return
                
                # Sort members to ensure directories are created before files
                members.sort(key=lambda member: member.name)
                
                # Split members by type
                directories = []
                regular_files = []
                symlinks = []
                hardlinks = []
                other_types = []
                
                for member in members:
                    if member.isdir():
                        directories.append(member)
                    elif member.isreg():
                        regular_files.append(member)
                    elif member.issym():
                        symlinks.append(member)
                    elif member.islnk():
                        hardlinks.append(member)
                    else:
                        other_types.append(member)
                
                # Extract in the correct order: directories, regular files, symlinks, hardlinks, others
                # This ensures targets exist before creating links to them
                
                # 1. First create all directories
                for member in directories:
                    # Determine output path
                    if not args.vulnerable:
                        output_path = self._sanitize_path(member.name, args.output_dir)
                    else:
                        output_path = os.path.join(args.output_dir, member.name)
                    
                    # Create directory
                    if not os.path.exists(output_path):
                        os.makedirs(output_path, exist_ok=True)
                    if args.verbose:
                        print(f"Created directory: {output_path}")
                    
                    # Set permissions if requested
                    if not args.normalize_permissions:
                        try:
                            os.chmod(output_path, member.mode & 0o777)
                        except:
                            print(f"Warning: Could not set permissions for {output_path}")
                
                # 2. Extract regular files
                for member in regular_files:
                    # Determine output path
                    if not args.vulnerable:
                        output_path = self._sanitize_path(member.name, args.output_dir)
                    else:
                        output_path = os.path.join(args.output_dir, member.name)
                    
                    # Create parent directories
                    self._create_parent_dirs(output_path)
                    
                    # Extract the file
                    with open(output_path, 'wb') as f:
                        f.write(tar_file.extractfile(member).read())
                    if args.verbose:
                        print(f"Extracted: {output_path}")
                    
                    # Set permissions if requested
                    if not args.normalize_permissions:
                        try:
                            os.chmod(output_path, member.mode & 0o777)
                        except:
                            print(f"Warning: Could not set permissions for {output_path}")
                
                # 3. Process symlinks
                for member in symlinks:
                    # Determine output path
                    if not args.vulnerable:
                        output_path = self._sanitize_path(member.name, args.output_dir)
                    else:
                        output_path = os.path.join(args.output_dir, member.name)
                    
                    # Create parent directories
                    self._create_parent_dirs(output_path)
                    
                    # Handle symlinks based on mode
                    if not args.vulnerable:
                        # In safe mode, create a regular file with info about the link
                        with open(output_path, 'w') as f:
                            f.write(f"symlink to: {member.linkname}")
                        if args.verbose:
                            print(f"Created file for symlink: {output_path} (points to {member.linkname})")
                    else:
                        # In vulnerable mode, create the actual symlink
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        try:
                            os.symlink(member.linkname, output_path)
                            if args.verbose:
                                print(f"Created symlink: {output_path} -> {member.linkname}")
                        except:
                            print(f"Error creating symlink: {member.name}")
                            # Fall back to file with info
                            with open(output_path, 'w') as f:
                                f.write(f"Failed to create symlink to: {member.linkname}")
                
                # 4. Process hardlinks (after regular files exist)
                for member in hardlinks:
                    # Determine output path
                    if not args.vulnerable:
                        output_path = self._sanitize_path(member.name, args.output_dir)
                    else:
                        output_path = os.path.join(args.output_dir, member.name)
                    
                    # Create parent directories
                    self._create_parent_dirs(output_path)
                    
                    # Handle hardlinks based on mode
                    if not args.vulnerable:
                        # In safe mode, create a regular file with info about the link
                        with open(output_path, 'w') as f:
                            f.write(f"hardlink to: {member.linkname}")
                        if args.verbose:
                            print(f"Created file for hardlink: {output_path} (points to {member.linkname})")
                    else:
                        # In vulnerable mode, create the actual hardlink if possible
                        # First, find the target
                        target_path = os.path.join(args.output_dir, member.linkname)
                        if os.path.exists(target_path):
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            try:
                                os.link(target_path, output_path)
                                if args.verbose:
                                    print(f"Created hardlink: {output_path} -> {target_path}")
                            except:
                                # Fall back to copying
                                shutil.copy2(target_path, output_path)
                                if args.verbose:
                                    print(f"Copied file (hardlink not supported): {output_path}")
                        else:
                            print(f"Warning: Hardlink target not found: {target_path}")
                            # Create a placeholder file
                            with open(output_path, 'w') as f:
                                f.write(f"Hardlink to: {member.linkname} (target not found)")
                
                # 5. Process other types
                for member in other_types:
                    if args.verbose:
                        print(f"Skipping unsupported file type: {member.name}")
                
                # Print summary
                if args.verbose:
                    print(f"Extraction complete: {len(members)} entries extracted to {args.output_dir}")
        
        except tarfile.ReadError:
            print(f"Error: {args.file} is not a valid TAR file")
        except Exception as e:
            print(f"Error extracting {args.file}: {e}")