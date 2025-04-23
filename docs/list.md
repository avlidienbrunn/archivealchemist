# Archive Alchemist: list Command

## Overview

The `list` command displays the contents of an archive, showing all files, directories, symlinks, and hardlinks. It can show either a simple list of filenames or a detailed view with file attributes, similar to `ls -l` in Unix/Linux.

## Syntax

```bash
./archive-alchemist.py -f <archive> [-t <type>] list [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--long`, `-l` | Show detailed listing with file attributes | 1 (True) | `--long 0` |

## Examples

### Basic Listing

```bash
# List files in an archive (default detailed view)
./archive-alchemist.py -f archive.zip list

# Equivalent to:
./archive-alchemist.py -f archive.zip list --long 1
```

### Simple Listing (Filenames Only)

```bash
# Show only filenames
./archive-alchemist.py -f archive.zip list --long 0

# Using the short form
./archive-alchemist.py -f archive.tar -t tar list -l 0
```

## Output Format

### Detailed Listing (--long 1)

For ZIP archives, the detailed output includes:
```
Permissions  Size       Modified             Name
-rw-r--r--   12345      2023-06-15 10:30:45  file.txt
drwxr-xr-x   0          2023-06-15 10:30:00  directory/
lrwxrwxrwx   0          2023-06-15 10:31:15  link.txt -> target.txt
```

For TAR archives, the detailed output includes:
```
Permissions  Owner/Group      Size       Modified             Name
-rw-r--r--   user/group       12345      2023-06-15 10:30:45  file.txt
drwxr-xr-x   user/group       0          2023-06-15 10:30:00  directory/
lrwxrwxrwx   user/group       0          2023-06-15 10:31:15  link.txt -> target.txt
-rwxr-xr-x   user/group       512        2023-06-15 10:32:00  hardlink.txt link to original.txt
```

### Simple Listing (--long 0)

```
Contents of archive.zip:
file.txt
directory/file2.txt
link.txt
```

## Notes and Warnings

- The permissions shown in the detailed listing reflect what's stored in the archive, which may not match the permissions that will be applied when files are extracted. This is especially true for ZIP archives, where some utilities have limited support for preserving Unix permissions.

- For symlinks, the detailed listing shows the symlink target with `->` after the filename.

- For hardlinks (in TAR archives), the detailed listing shows the hardlink target with `link to` after the filename.

- Empty directories are included in the listing with a trailing slash (`/`).

- ZIP archives store timestamps with less precision than TAR archives (ZIP stores to the nearest 2 seconds), so the modification times shown might differ slightly from the original file times.

- For compressed archives (tar.gz, tar.xz, tar.bz2), the list command decompresses the archive in memory to read its contents, which may use more resources for large archives.

- By default, the listing is sorted by filename. This helps maintain consistent output for testing and scripting purposes.