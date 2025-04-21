"""
Base handler for archive operations.
Defines the interface that all archive handlers must implement.
"""

import os
from abc import ABC, abstractmethod

class BaseArchiveHandler(ABC):
    """Base class for archive handlers."""
    
    @abstractmethod
    def add(self, args):
        """Add a file or symlink to the archive."""
        pass
    
    @abstractmethod
    def replace(self, args):
        """Replace a file in the archive."""
        pass
    
    @abstractmethod
    def append(self, args):
        """Append content to a file in the archive."""
        pass
    
    @abstractmethod
    def modify(self, args):
        """Modify file attributes in the archive."""
        pass
    
    @abstractmethod
    def remove(self, args):
        """Remove a file or directory from the archive."""
        pass

    @abstractmethod
    def list(self, args):
        """List the contents of the archive."""
        pass

    @abstractmethod
    def extract(self, args):
        """Extract files from the archive."""
        pass

    def _sanitize_path(self, path, output_dir):
        """Sanitize a path to prevent path traversal attacks.
        
        Args:
            path: The path to sanitize.
            output_dir: The base output directory.
            
        Returns:
            A safe path within the output directory.
        """
        # Remove any leading slashes and drive letters (Windows)
        path = os.path.normpath(path)
        if os.path.isabs(path):
            # For absolute paths, just use the filename/last component
            path = os.path.basename(path)
        
        # Remove any parent directory references to prevent traversal
        parts = []
        for part in path.split(os.sep):
            if part == '.' or part == '':
                continue
            if part == '..':
                continue  # Skip parent directory references
            parts.append(part)
        
        # Join the safe parts
        safe_path = os.path.join(*parts) if parts else ''
        
        # Join with the output directory
        return os.path.join(output_dir, safe_path)

    def _is_safe_path(self, path, output_dir):
        """Check if a path is safe to extract to.
        
        Args:
            path: The path to check.
            output_dir: The base output directory.
            
        Returns:
            True if the path is safe, False otherwise.
        """
        # Normalize both paths for comparison
        path = os.path.normpath(os.path.join(output_dir, path))
        output_dir = os.path.normpath(output_dir)
        
        # The normalized path should start with the output directory
        return os.path.commonprefix([path, output_dir]) == output_dir and '..' not in path

    def _create_parent_dirs(self, path):
        """Create parent directories for a path if they don't exist.
        
        Args:
            path: The path to create parent directories for.
        """
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

    def format_mode(self, mode):
        """Format a file mode as a permission string (like ls -l).
        
        Args:
            mode: The file mode as an integer.
            
        Returns:
            A string representation of the file permissions.
        """
        if mode is None:
            return "----------"
            
        result = ""
        
        # File type
        if mode & 0o170000 == 0o120000:  # Symlink
            result += "l"
        elif mode & 0o170000 == 0o040000:  # Directory
            result += "d"
        else:  # Regular file
            result += "-"
        
        # User permissions
        result += "r" if mode & 0o400 else "-"
        result += "w" if mode & 0o200 else "-"
        if mode & 0o4000:  # Setuid
            result += "s" if mode & 0o100 else "S"
        else:
            result += "x" if mode & 0o100 else "-"
        
        # Group permissions
        result += "r" if mode & 0o40 else "-"
        result += "w" if mode & 0o20 else "-"
        if mode & 0o2000:  # Setgid
            result += "s" if mode & 0o10 else "S"
        else:
            result += "x" if mode & 0o10 else "-"
        
        # Other permissions
        result += "r" if mode & 0o4 else "-"
        result += "w" if mode & 0o2 else "-"
        if mode & 0o1000:  # Sticky
            result += "t" if mode & 0o1 else "T"
        else:
            result += "x" if mode & 0o1 else "-"
        
        return result

    def get_raw_bytes(self, str):
        # This would take 0 minutes to fix in python2. Thanks, asshole encoding enforcers.
        return str.encode('utf-8', errors='surrogateescape')

    def add_directory(self, args):
        """Add a directory recursively to the archive.
        
        Args:
            args: Command-line arguments.
        """
        if not os.path.isdir(args.content_directory):
            print(f"Error: {args.content_directory} is not a directory")
            return
        
        # Track directories we've added to avoid duplicates
        added_dirs = set()
        
        # Function to ensure a directory and its parents exist in the archive
        def ensure_directory(dir_path):
            # Skip if already added
            if dir_path in added_dirs:
                return
                
            # Get parent directories too (excluding the root)
            parts = dir_path.split('/')
            for i in range(1, len(parts)):
                parent = '/'.join(parts[:i])
                if parent and parent not in added_dirs:
                    # Calculate the correct directory path relative to content_directory
                    # For a parent directory in the archive path, we need to map to the content_directory
                    parent_rel_path = '/'.join(parts[1:i]) if len(parts) > i else ''
                    parent_fs_path = os.path.join(args.content_directory, parent_rel_path)
                    
                    if os.path.exists(parent_fs_path) and os.path.isdir(parent_fs_path):
                        # Get the actual directory permissions
                        dir_stat = os.stat(parent_fs_path)
                        dir_mode = dir_stat.st_mode & 0o777  # Extract permission bits
                        # Use args.mode if specified, otherwise use the directory's actual mode
                        mode_to_use = args.mode if hasattr(args, 'mode') and args.mode is not None else dir_mode
                    else:
                        # Directory doesn't exist in source, use default or specified mode
                        mode_to_use = args.mode if hasattr(args, 'mode') and args.mode is not None else 0o755
                    
                    if args.verbose:
                        print(f"Adding directory {parent}/")
                    
                    # Create directory entry (ends with /)
                    dir_args = type('Args', (), {
                        'file': args.file,
                        'path': f"{parent}/",
                        'content': b'',  # Empty content for directory
                        'content_file': None,
                        'content_directory': None,
                        'symlink': None,
                        'hardlink': None,
                        'mode': mode_to_use,
                        'uid': args.uid if hasattr(args, 'uid') else None,
                        'gid': args.gid if hasattr(args, 'gid') else None,
                        'mtime': args.mtime if hasattr(args, 'mtime') else None,
                        'setuid': args.setuid if hasattr(args, 'setuid') else False,
                        'setgid': args.setgid if hasattr(args, 'setgid') else False,
                        'sticky': args.sticky if hasattr(args, 'sticky') else False,
                        'verbose': False  # Avoid duplicate verbose output
                    })
                    
                    # Add the directory entry
                    self.add(dir_args)
                    added_dirs.add(parent)
            
            # Add the directory itself - calculate correct relative path
            dir_rel_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
            dir_fs_path = os.path.join(args.content_directory, dir_rel_path)
            
            if os.path.exists(dir_fs_path) and os.path.isdir(dir_fs_path):
                # Get the actual directory permissions
                dir_stat = os.stat(dir_fs_path)
                dir_mode = dir_stat.st_mode & 0o777  # Extract permission bits
                # Use args.mode if specified, otherwise use the directory's actual mode
                mode_to_use = args.mode if hasattr(args, 'mode') and args.mode is not None else dir_mode
            else:
                # Directory doesn't exist in source, use default or specified mode
                mode_to_use = args.mode if hasattr(args, 'mode') and args.mode is not None else 0o755
            
            if args.verbose:
                print(f"Adding directory {dir_path}/")
                
            # Create directory entry
            dir_args = type('Args', (), {
                'file': args.file,
                'path': f"{dir_path}/",
                'content': b'',  # Empty content for directory
                'content_file': None,
                'content_directory': None,
                'symlink': None,
                'hardlink': None,
                'mode': mode_to_use,
                'uid': args.uid if hasattr(args, 'uid') else None,
                'gid': args.gid if hasattr(args, 'gid') else None,
                'mtime': args.mtime if hasattr(args, 'mtime') else None,
                'setuid': args.setuid if hasattr(args, 'setuid') else False,
                'setgid': args.setgid if hasattr(args, 'setgid') else False,
                'sticky': args.sticky if hasattr(args, 'sticky') else False,
                'verbose': False  # Avoid duplicate verbose output
            })
            
            # Add the directory entry
            self.add(dir_args)
            added_dirs.add(dir_path)
        
        # Walk the directory (explicitly not following symlinks)
        for root, dirs, files in os.walk(args.content_directory, followlinks=False):
            # Calculate the relative path of the current directory
            rel_dir = os.path.relpath(root, args.content_directory)
            if rel_dir == '.':
                rel_dir = ''
                
            # Construct the archive directory path
            archive_dir = os.path.join(args.path, rel_dir).replace(os.path.sep, '/')
            if archive_dir:
                archive_dir = archive_dir.replace('//', '/').rstrip('/')
                
            # Ensure the directory exists in the archive
            if archive_dir:
                ensure_directory(archive_dir)
            
            # Process directory symlinks
            for dirname in dirs:
                dir_path = os.path.join(root, dirname)
                
                # Calculate relative path within archive
                rel_path = os.path.relpath(dir_path, args.content_directory)
                archive_path = os.path.join(args.path, rel_path).replace(os.path.sep, '/')
                
                # If it's a symlink, add it as a symlink
                if os.path.islink(dir_path):
                    target = os.readlink(dir_path)
                    
                    if args.verbose:
                        print(f"Adding directory symlink {dir_path} -> {target} as {archive_path}")
                    
                    symlink_args = type('Args', (), {
                        'file': args.file,
                        'path': archive_path,
                        'content': None,
                        'content_file': None,
                        'content_directory': None,
                        'symlink': target,
                        'hardlink': None,
                        'mode': args.mode if hasattr(args, 'mode') else None,
                        'uid': args.uid if hasattr(args, 'uid') else None,
                        'gid': args.gid if hasattr(args, 'gid') else None,
                        'mtime': args.mtime if hasattr(args, 'mtime') else None,
                        'setuid': args.setuid if hasattr(args, 'setuid') else False,
                        'setgid': args.setgid if hasattr(args, 'setgid') else False,
                        'sticky': args.sticky if hasattr(args, 'sticky') else False,
                        'verbose': args.verbose
                    })
                    
                    self.add(symlink_args)
                # Otherwise, it's a regular directory, already handled above
            
            # Process regular files and file symlinks
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # Calculate relative path within archive
                rel_path = os.path.relpath(file_path, args.content_directory)
                archive_path = os.path.join(args.path, rel_path).replace(os.path.sep, '/')
                
                # If it's a symlink, add it as a symlink
                if os.path.islink(file_path):
                    target = os.readlink(file_path)
                    
                    if args.verbose:
                        print(f"Adding symlink {file_path} -> {target} as {archive_path}")
                    
                    symlink_args = type('Args', (), {
                        'file': args.file,
                        'path': archive_path,
                        'content': None,
                        'content_file': None,
                        'content_directory': None,
                        'symlink': target,
                        'hardlink': None,
                        'mode': args.mode if hasattr(args, 'mode') else None,
                        'uid': args.uid if hasattr(args, 'uid') else None,
                        'gid': args.gid if hasattr(args, 'gid') else None,
                        'mtime': args.mtime if hasattr(args, 'mtime') else None,
                        'setuid': args.setuid if hasattr(args, 'setuid') else False,
                        'setgid': args.setgid if hasattr(args, 'setgid') else False,
                        'sticky': args.sticky if hasattr(args, 'sticky') else False,
                        'verbose': args.verbose
                    })
                    
                    self.add(symlink_args)
                else:
                    # Regular file
                    file_stat = os.stat(file_path)
                    file_mode = file_stat.st_mode & 0o777  # Extract permission bits
                    if args.verbose:
                        print(f"Adding file {file_path} as {archive_path} with mode {oct(file_mode)} {args.mode}")
                    
                    file_args = type('Args', (), {
                        'file': args.file,
                        'path': archive_path,
                        'content': None,
                        'content_file': file_path,
                        'content_directory': None,
                        'symlink': None,
                        'hardlink': None,
                        'mode': args.mode if args.mode != None else file_mode,
                        'uid': args.uid if hasattr(args, 'uid') else None,
                        'gid': args.gid if hasattr(args, 'gid') else None,
                        'mtime': args.mtime if hasattr(args, 'mtime') else None,
                        'setuid': args.setuid if hasattr(args, 'setuid') else False,
                        'setgid': args.setgid if hasattr(args, 'setgid') else False,
                        'sticky': args.sticky if hasattr(args, 'sticky') else False,
                        'verbose': args.verbose
                    })
                    
                    self.add(file_args)

    def get_content(self, args):
        """Get content from either --content or --content-file options.
        
        Args:
            args: The command-line arguments.
            
        Returns:
            The content as a string.
            
        Raises:
            ValueError: If both --content and --content-file are specified.
            FileNotFoundError: If the content file doesn't exist.
        """
        if args.content and args.content_file:
            raise ValueError("Cannot specify both --content and --content-file")
            
        if args.content_file:
            # Check if the file exists
            if not os.path.exists(args.content_file):
                raise FileNotFoundError(f"Content file not found: {args.content_file}")
                
            # Read the file content
            with open(args.content_file, 'rb') as f:
                return f.read()
        
        if args.content and type(args.content) == str:
            args.content = self.get_raw_bytes(args.content)
        # Return the content argument or an empty string if neither is specified
        return args.content if args.content else b""
    
    def apply_special_bits(self, mode, args):
        """Apply special permission bits if requested."""
        if args.setuid:
            mode |= 0o4000
        if args.setgid:
            mode |= 0o2000
        if args.sticky:
            mode |= 0o1000
        return mode