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