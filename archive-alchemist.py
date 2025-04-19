#!/usr/bin/env python3
"""
Archive Alchemist - A tool for creating specially crafted archives for security testing.

This tool allows security researchers to create archives with various attack patterns
like path traversal, symlinks, hardlinks, etc. to test extraction vulnerabilities.
"""

import sys
sys.dont_write_bytecode = True

import argparse

# Import handlers for different archive types
from handlers.zip_handler import ZipHandler
from handlers.tar_handler import TarHandler


class ArchiveAlchemist:
    def __init__(self):
        self.parser = self._create_parser()
        self.handlers = {
            "zip": ZipHandler(),
            "tar": TarHandler(compressed=False),
            "tar.gz": TarHandler(compressed=True)
        }
        
    def _create_parser(self):
        """Create the command line argument parser."""
        parser = argparse.ArgumentParser(
            description="Archive Alchemist - Create specially crafted archives for security testing.",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Global options
        parser.add_argument("-f", "--file", required=True, help="Archive file to create or modify")
        parser.add_argument("-t", "--type", choices=["zip", "tar", "tar.gz"], default="zip",
                        help="Archive type (default: zip)")
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Ensure subcommands appear in help (Python 3 compatibility fix)
        subparsers.required = True
        
        # Add command
        add_parser = subparsers.add_parser("add", help="Add files to the archive")
        add_parser.add_argument("path", help="Path within the archive")
        add_parser.add_argument("--content", help="Content to add to the file")
        add_parser.add_argument("--content-file", help="Path to a local file whose content should be added")
        add_parser.add_argument("--symlink", help="Create a symlink to this target")
        add_parser.add_argument("--hardlink", help="Create a hardlink to this target")
        add_parser.add_argument("--mode", type=lambda x: int(x, 8), help="File mode (octal)")
        add_parser.add_argument("--uid", type=int, help="User ID")
        add_parser.add_argument("--gid", type=int, help="Group ID")
        add_parser.add_argument("--mtime", type=int, help="Modification time")
        add_parser.add_argument("--setuid", action="store_true", help="Set the setuid bit")
        add_parser.add_argument("--setgid", action="store_true", help="Set the setgid bit")
        add_parser.add_argument("--sticky", action="store_true", help="Set the sticky bit")
        
        # Replace command
        replace_parser = subparsers.add_parser("replace", help="Replace files in the archive")
        replace_parser.add_argument("path", help="Path within the archive")
        replace_parser.add_argument("--content", help="New content for the file")
        replace_parser.add_argument("--content-file", help="Path to a local file whose content should be used")
        replace_parser.add_argument("--require-content", action="store_true", default=True, 
                                help=argparse.SUPPRESS)  # Hidden option to maintain backward compatibility
        
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

        # Remove command
        remove_parser = subparsers.add_parser("remove", help="Remove files from the archive")
        remove_parser.add_argument("path", help="Path within the archive to remove")
        
        return parser
    
    def _get_handler(self, args):
        """Get the appropriate handler for the archive type."""
        return self.handlers[args.type]
    
    def run(self):
        """Run the main program."""
        args = self.parser.parse_args()
        
        # Command will be required by parser, but for clarity:
        if args.command is None:
            self.parser.print_help()
            return
        
        handler = self._get_handler(args)
        
        if args.command == "add":
            handler.add(args)
        elif args.command == "replace":
            handler.replace(args)
        elif args.command == "append":
            handler.append(args)
        elif args.command == "modify":
            handler.modify(args)
        elif args.command == "remove":
            handler.remove(args)
        else:
            print(f"Error: Unknown command {args.command}")


if __name__ == "__main__":
    ArchiveAlchemist().run()