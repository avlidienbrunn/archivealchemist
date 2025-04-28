# Archive Alchemist: remove Command

## Overview

The `remove` (or the alias, `rm`) command deletes files, directories, symlinks, or hardlinks from an archive. By default, it removes directories recursively, but this behavior can be controlled with the `--recursive` flag.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] remove <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive to remove (required) | N/A | `file.txt`, `dir/`, `symlink.txt` |
| `--recursive`, `-r` | Remove entries recursively | 1 (True) | `--recursive 0` |

## Examples

### Removing a Single File

```bash
# Remove a file from a ZIP archive
./archive-alchemist.py archive.zip remove file.txt

# Remove a file from a TAR archive
./archive-alchemist.py archive.tar -t tar remove config/settings.conf
```

### Removing a Directory Recursively (Default)

```bash
# Remove a directory and all its contents
./archive-alchemist.py archive.zip remove config/

# This is equivalent to:
./archive-alchemist.py archive.zip remove config/ --recursive 1
```

### Removing a Directory Non-recursively

```bash
# Remove only the directory entry, not its contents
./archive-alchemist.py archive.zip remove config/ --recursive 0
```

With `--recursive 0`, only the exact path specified will be removed. If the path is a directory, only the directory entry itself is removed, while the files inside the directory remain in the archive.

### Removing a Symlink or Hardlink

```bash
# Remove a symlink
./archive-alchemist.py archive.tar -t tar remove link.txt

# Remove a hardlink
./archive-alchemist.py archive.tar -t tar remove hardlink.txt
```

## Notes and Warnings

- When removing a directory with `--recursive 1` (the default), all files and subdirectories within that directory will also be removed.

- If `--recursive 0` is specified when removing a directory, only the directory entry itself is removed, not its contents. This may leave orphaned files in the archive that are still accessible but no longer have their parent directory.