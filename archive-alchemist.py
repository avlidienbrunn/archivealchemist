#!/usr/bin/env python3
"""
Archive Alchemist - A tool for creating specially crafted archives for security testing.

This tool allows security researchers to create archives with various attack patterns
like path traversal, symlinks, hardlinks, etc. to test extraction vulnerabilities.
"""

import sys
sys.dont_write_bytecode = True # no __pycache__ bs

import argparse, os, tarfile
from handlers.zip_handler import ZipHandler
from handlers.tar_handler import TarHandler


class ArchiveAlchemist:
    def __init__(self):
        self.parser = self._create_parser()
        self.handlers = {
            "zip": ZipHandler(orphaned_mode=False),
            "ziporphan": ZipHandler(orphaned_mode=True),
            "tar": TarHandler(compressed=False),
            "tar.gz": TarHandler(compressed="gz"),
            "tar.xz": TarHandler(compressed="xz"),
            "tar.bz2": TarHandler(compressed="bz2")
        }
        
    def _detect_archive_type(self, filename):
        """Detect the archive type based on file magic bytes."""
        # Check if file exists before attempting detection
        if not os.path.exists(filename):
            # For non-existent files, detect based on extension
            return self._detect_from_extension(filename)
        
        # Read the first few bytes to identify the file type
        try:
            with open(filename, 'rb') as f:
                magic_bytes = f.read(8)  # Read first 8 bytes
                
                # ZIP: Starts with 'PK\x03\x04'
                if magic_bytes.startswith(b'PK\x03\x04'):
                    return 'zip'
                
                # GZIP: Starts with 0x1F 0x8B
                if magic_bytes.startswith(b'\x1F\x8B'):
                    return 'tar.gz'
                    
                # XZ: Starts with 0xFD '7zXZ'
                if magic_bytes.startswith(b'\xFD\x37\x7A\x58\x5A\x00'):
                    return 'tar.xz'
                    
                # BZ2: Starts with 'BZh'
                if magic_bytes.startswith(b'BZh'):
                    return 'tar.bz2'
                
                # TAR: Check for tar format
                if self._is_tar_file(filename):
                    return 'tar'
                
                # If no magic bytes match, fall back to extension-based detection
                return self._detect_from_extension(filename)
        except:
            # If there's any error reading the file, fall back to extension-based detection
            return self._detect_from_extension(filename)

    def _is_tar_file(self, filename):
        """Check if a file is a valid TAR archive.
        
        Args:
            filename: The name of the file to check.
            
        Returns:
            True if the file is a valid TAR archive, False otherwise.
        """
        try:
            # Try to open the file as a TAR archive
            with tarfile.open(filename, 'r') as _:
                return True
        except:
            return False

    def _detect_from_extension(self, filename):
        """Detect the archive type based on the file extension."""
        # Convert to lowercase for case-insensitive comparison
        lower_filename = filename.lower()
        
        if lower_filename.endswith('.tar.gz') or lower_filename.endswith('.tgz'):
            return 'tar.gz'
        elif lower_filename.endswith('.tar.xz') or lower_filename.endswith('.txz'):
            return 'tar.xz'
        elif lower_filename.endswith('.tar.bz2') or lower_filename.endswith('.tbz2'):
            return 'tar.bz2'
        elif lower_filename.endswith('.tar'):
            return 'tar'
        else:
            # Default to ZIP
            return 'zip'

    def _create_parser(self):
        asciiart = '''
                _     _           
               | |   (_)                 .---.          
  __ _ _ __ ___| |__  ___   _____       _\\___/_ 
 / _` | '__/ __| '_ \\| \\ \\ / / _ \\       )\\_/(
| (_| | | | (__| | | | |\\ V /  __/      /     \\
 \\__,_|_|  \\___|_| |_|_| \\_/ \\___|     /       \\             _      _                    _     _ 
                                      /         \\           | |    | |                  (_)   | |  
                                     /~~~~~~~~~~~\\      __ _| | ___| |__   ___ _ __ ___  _ ___| |_ 
                                    /    tar   gz \\    / _` | |/ __| '_ \\ / _ \\ '_ ` _ \\| / __| __|
                                   ( zip    bz2    )  | (_| | | (__| | | |  __/ | | | | | \\__ \\ |_
                                    `-------------'    \\__,_|_|\\___|_| |_|\\___|_| |_| |_|_|___/\\__| '''
        """Create the command line argument parser."""
        parser = argparse.ArgumentParser(
            description=asciiart,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Global options
        parser.add_argument("file", help="Archive file to create or modify")
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
        class TypeAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                setattr(namespace, 'type', values)
                setattr(namespace, 'type_specified', True)
        parser.add_argument("-t", "--type", choices=["zip", "tar", "tar.gz", "tar.xz", "tar.bz2"], default="zip",
                  action=TypeAction, help="Archive type (default: auto-detect from file extension)")
        parser.add_argument("-fo", "--find-orphaned", action="store_true", 
                  help="Find orphaned entries in ZIP files (enables deep scanning for corrupt/malicious archives)")
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Ensure subcommands appear in help (Python 3 compatibility fix)
        subparsers.required = True
        
        # Add command
        add_parser = subparsers.add_parser("add", help="Add files to the archive")
        add_parser.add_argument("path", help="Path within the archive")
        add_parser.add_argument("--content", help="Content to add to the file")
        add_parser.add_argument("--content-file", help="Path to a local file whose content should be added")
        add_parser.add_argument("--content-directory", help="Path to a local directory to add recursively")
        add_parser.add_argument("--symlink", help="Create a symlink to this target")
        add_parser.add_argument("--hardlink", help="Create a hardlink to this target")
        add_parser.add_argument("--mode", type=lambda x: int(x, 8), help="File mode (octal)")
        add_parser.add_argument("--uid", type=int, help="User ID")
        add_parser.add_argument("--gid", type=int, help="Group ID")
        add_parser.add_argument("--mtime", type=int, help="Modification time")
        add_parser.add_argument("--setuid", action="store_true", help="Set the setuid bit")
        add_parser.add_argument("--setgid", action="store_true", help="Set the setgid bit")
        add_parser.add_argument("--sticky", action="store_true", help="Set the sticky bit")
        add_parser.add_argument("--unicodepath", help="Set the ZIP Unicode Path field")
        
        # Replace command
        replace_parser = subparsers.add_parser("replace", help="Replace files in the archive")
        replace_parser.add_argument("path", help="Path within the archive")
        replace_parser.add_argument("--content", help="New content for the file")
        replace_parser.add_argument("--content-file", help="Path to a local file whose content should be used")
        replace_parser.add_argument("--require-content", action="store_true", default=True, 
                                help=argparse.SUPPRESS)  # Hidden option to maintain backward compatibility
        replace_parser.add_argument("--content-directory", help="Path to a local directory to add recursively")
        replace_parser.add_argument("--symlink", help="Create a symlink to this target")
        replace_parser.add_argument("--hardlink", help="Create a hardlink to this target")
        replace_parser.add_argument("--mode", type=lambda x: int(x, 8), help="File mode (octal)")
        replace_parser.add_argument("--uid", type=int, help="User ID")
        replace_parser.add_argument("--gid", type=int, help="Group ID")
        replace_parser.add_argument("--mtime", type=int, help="Modification time")
        replace_parser.add_argument("--setuid", action="store_true", help="Set the setuid bit")
        replace_parser.add_argument("--setgid", action="store_true", help="Set the setgid bit")
        replace_parser.add_argument("--sticky", action="store_true", help="Set the sticky bit")
        replace_parser.add_argument("--unicodepath", help="Set the ZIP Unicode Path field")
        
        # Append command
        append_parser = subparsers.add_parser("append", help="Append to files in the archive")
        append_parser.add_argument("path", help="Path within the archive")
        append_parser.add_argument("--content", help="Content to append to the file")
        append_parser.add_argument("--content-file", help="Path to a local file whose content should be appended")
        append_parser.add_argument("--require-content", action="store_true", default=True,
                                help=argparse.SUPPRESS)  # Hidden option to maintain backward compatibility
        
        # Modify command
        modify_parser = subparsers.add_parser("modify", help="Modify file attributes")
        modify_parser.add_argument("path", help="Path within the archive")
        modify_parser.add_argument("--mode", type=lambda x: int(x, 8), help="File mode (octal)")
        modify_parser.add_argument("--uid", type=int, help="User ID")
        modify_parser.add_argument("--gid", type=int, help="Group ID")
        modify_parser.add_argument("--mtime", type=int, help="Modification time")
        modify_parser.add_argument("--setuid", action="store_true", help="Set the setuid bit")
        modify_parser.add_argument("--setgid", action="store_true", help="Set the setgid bit")
        modify_parser.add_argument("--sticky", action="store_true", help="Set the sticky bit")
        modify_parser.add_argument("--symlink", help="Convert file to a symlink pointing to this target")
        modify_parser.add_argument("--hardlink", help="Convert file to a hardlink pointing to this target")
        modify_parser.add_argument("--unicodepath", help="Set the ZIP Unicode Path field")


        # Remove command
        remove_parser = subparsers.add_parser("remove", help="Remove files from the archive")
        remove_parser.add_argument("path", help="Path within the archive to remove")
        remove_parser.add_argument("--recursive", "-r", type=int, default=1, help="Remove entries recursively (default 1/true)")
        # Make rm alias for remove
        subparsers._name_parser_map["rm"] = remove_parser

        # List command
        list_parser = subparsers.add_parser("list", help="List contents of the archive")
        list_parser.add_argument("--long", "-l", type=int, default=1, help="Show detailed listing with file attributes")
        list_parser.add_argument("--longlong", "-ll", action="store_true", help="Show very detailed listing with all header information")
        # Make ls alias for list
        subparsers._name_parser_map["ls"] = list_parser

        # Extract command
        extract_parser = subparsers.add_parser("extract", help="Extract files from the archive")
        extract_parser.add_argument("--path", help="Path within the archive to extract (default: extract all)")
        extract_parser.add_argument("--output-dir", "-o", default=".", help="Directory to extract files to (default: current directory)")
        extract_parser.add_argument("--vulnerable", action="store_true", help="Allow potentially unsafe extractions (absolute paths, path traversal, etc.)")
        extract_parser.add_argument("--normalize-permissions", action="store_true", help="Normalize file permissions during extraction (don't preserve original permissions)")

        # Read command
        read_parser = subparsers.add_parser("read", help="Extract files from the archive")
        read_parser.add_argument("path", help="Path within the archive")
        read_parser.add_argument("--index", "-i", type=int, default=0, help="Index to read (in case there are several entries with the same name), default=0.")
        # Make cat alias for read
        subparsers._name_parser_map["cat"] = read_parser
        
        # Polyglot command
        polyglot_parser = subparsers.add_parser("polyglot", help="Create a polyglot file by prepending content to an archive")
        polyglot_parser.add_argument("--content", help="Content to prepend to the file")
        polyglot_parser.add_argument("--content-file", help="Path to a local file whose content should be prepended")

        return parser
    
    def _get_handler(self, args):
        """Get the appropriate handler for the archive type."""
        handler_type = args.type
        # Use ziporphan handler when find_orphaned flag is set and type is zip
        if handler_type == "zip" and hasattr(args, 'find_orphaned') and args.find_orphaned:
            handler_type = "ziporphan"
        return self.handlers[handler_type]
    
    def run(self):
        """Run the main program."""
        args = self.parser.parse_args()
        
        # Initialize type_specified if it's not already set
        if not hasattr(args, 'type_specified'):
            args.type_specified = False
        
        # Command will be required by parser, but for clarity:
        if args.command is None:
            self.parser.print_help()
            return
        
        # Detect archive type if not specified
        if not args.type_specified and args.file:
            detected_type = self._detect_archive_type(args.file)
            args.type = detected_type
            if args.verbose:
                print(f"Auto-detected archive type: {args.type}")
        
        handler = self._get_handler(args)

        if args.type != 'zip' and getattr(args, 'unicodepath', None):
            print(f"Error: --unicodepath can only be used in zip (provided type: {args.type})")
            exit()
        
        if args.command == "add":
            if getattr(args, 'content_directory', None):
                handler.add_directory(args)
            else:
                handler.add(args)
        elif args.command == "replace":
            if getattr(args, 'content_directory', None):
                handler.remove(args)
                handler.add_directory(args)
            else:
                handler.replace(args)
        elif args.command == "append":
            handler.append(args)
        elif args.command == "modify":
            handler.modify(args)
        elif args.command in ["remove", "rm"]:
            handler.remove(args)
        elif args.command in ["list", "ls"]:
            handler.list(args)
        elif args.command == "extract":
            handler.extract(args)
        elif args.command in ["read", "cat"]:
            handler.read(args)
        elif args.command == "polyglot":
            handler.polyglot(args)
        else:
            print(f"Error: Unknown command {args.command}")


if __name__ == "__main__":
    ArchiveAlchemist().run()