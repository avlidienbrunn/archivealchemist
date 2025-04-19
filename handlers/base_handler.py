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
            with open(args.content_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Return the content argument or an empty string if neither is specified
        return args.content if args.content else ""
    
    def create_temp_file(self, content=None):
        """Create a temporary file with optional content."""
        fd, temp_path = tempfile.mkstemp()
        try:
            if content is not None:
                with os.fdopen(fd, 'w') as f:
                    f.write(content)
            else:
                os.close(fd)
        except:
            os.close(fd)
            os.unlink(temp_path)
            raise
            
        return temp_path
    
    def apply_special_bits(self, mode, args):
        """Apply special permission bits if requested."""
        if args.setuid:
            mode |= 0o4000
        if args.setgid:
            mode |= 0o2000
        if args.sticky:
            mode |= 0o1000
        return mode