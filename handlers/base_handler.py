"""
Base handler for archive operations.
Defines the interface that all archive handlers must implement.
"""

import os
import tempfile
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

    def python_is_fing_ridiculous(self, str):
        # This would take 0 minutes to fix in python2. Thanks, asshole encoding enforcers.
        return str.encode('utf-8', errors='surrogateescape')

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
            args.content = self.python_is_fing_ridiculous(args.content)
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