# Archive Alchemist: replace Command

## Overview

The `replace` command replaces existing files or directories in an archive with new content, symlinks, hardlinks, or entire directory structures. Under the hood it uses `remove` and `replace` to ensure consistency in command functionality.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] replace <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive to replace (required) | N/A | `file.txt`, `dir/file.js`, `config/` |
| `--content` | New text content for the file | Empty | `--content "console.log('replaced')"` |
| `--content-file` | Path to a local file whose content should be used | None | `--content-file /path/to/local/file.txt` |
| `--content-directory` | Path to a local directory to replace with | None | `--content-directory /path/to/local/dir` |
| `--symlink` | Convert file to a symlink pointing to this target | None | `--symlink "/etc/passwd"` |
| `--hardlink` | Convert file to a hardlink pointing to this target | None | `--hardlink "target.txt"` |
| `--mode` | File mode in octal notation | Original mode | `--mode 0755` |
| `--uid` | User ID | Original UID | `--uid 0` |
| `--gid` | Group ID | Original GID | `--gid 0` |
| `--mtime` | Modification time (Unix timestamp) | Original mtime | `--mtime 1609459200` |
| `--setuid` | Set the setuid bit | False | `--setuid` |
| `--setgid` | Set the setgid bit | False | `--setgid` |
| `--sticky` | Set the sticky bit | False | `--sticky` |

**Note**: You can specify only one of `--content`, `--content-file`, `--content-directory`, `--symlink`, or `--hardlink`.

## Examples

### Replacing a File with New Content

```bash
# Replace with inline content
./archive-alchemist.py archive.zip replace config.json --content '{"version": "2.0", "updated": true}'

# Replace with content from another file
./archive-alchemist.py archive.tar replace settings.conf --content-file /path/to/new/settings.conf
```

### Converting a Regular File to a Symlink

```bash
# Convert a regular file to a symlink
./archive-alchemist.py archive.tar -t tar replace hello.txt --symlink "/etc/motd"
```

### Converting a Regular File to a Hardlink (TAR only)

```bash
# Convert a regular file to a hardlink
./archive-alchemist.py archive.tar -t tar replace copy.txt --hardlink "original.txt"
```

**Note**: ZIP format doesn't support true hardlinks. When replacing with a hardlink in a ZIP file, Archive Alchemist creates a regular file with the target path as its content.

### Replacing and Changing Permissions

```bash
# Replace a file and change its permissions
./archive-alchemist.py archive.zip replace script.sh --content-file /path/to/new/script.sh --mode 0755

# Replace a file and set the setuid bit
./archive-alchemist.py archive.tar -t tar replace binary --content-file /path/to/exploit --mode 0755 --setuid --uid 0
```

### Replacing an Entire Directory

```bash
# Replace a directory with a local directory structure
./archive-alchemist.py archive.zip replace website/ --content-directory /path/to/updated/website

# Replace a directory and set custom permissions for all files
./archive-alchemist.py archive.tar -t tar replace config/ --content-directory /path/to/new/config --mode 0600
```

When using `--content-directory`:
- All existing files under the specified path are removed
- The entire directory structure from the local directory is added
- File permissions are preserved from the source directory unless overridden with `--mode`
- Directory structure and empty directories are maintained
- Symlinks in the source directory are added as symlinks in the archive

## Advanced Examples

### Replacing Files for Security Testing

```bash
# Replace a configuration file with a malicious one
./archive-alchemist.py target.zip replace config/settings.xml --content-file evil-settings.xml

# Convert a regular file to a symlink for a symlink attack
./archive-alchemist.py package.tar -t tar replace .profile --symlink "/etc/shadow"
```

### Updating Timestamps

```bash
# Replace a file and set a specific modification time (January 1, 2021)
./archive-alchemist.py archive.zip replace log.txt --content "Event occurred" --mtime 1609459200
```

### Replacing with Special Permission Bits

```bash
# Replace with sticky bit directory
./archive-alchemist.py archive.tar -t tar replace tmp/ --content-directory /path/to/new/tmp --mode 01777 --sticky
```

## Notes and Warnings

- The `replace` command works by first removing the specified path and then adding the new content. It effectively combines the functionality of the `remove` and `add` commands.

- When replacing directories with `--content-directory`, all existing files under that directory are removed by default.