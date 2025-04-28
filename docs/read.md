# Archive Alchemist: read Command

## Overview

The `read` (or the alias, `cat`) command extracts and displays the content of a specific file from an archive to standard output. When multiple entries with the same name exist in an archive, you can specify which instance to read using the `--index` option.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] read <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive to read (required) | N/A | `file.txt`, `config/settings.json` |
| `--index`, `-i` | Index of the entry to read when multiple entries have the same name | 0 (first entry) | `--index 1` |

## Examples

### Reading a Regular File

```bash
# Read the content of a file in a ZIP archive
./archive-alchemist.py archive.zip read README.txt
```

### Reading Specific Entries with the Same Name

```bash
# Read the first instance of duplicate.txt (index 0)
./archive-alchemist.py archive.zip read duplicate.txt

# Read the second instance of duplicate.txt (index 1)
./archive-alchemist.py archive.zip read duplicate.txt --index 1

# Read the third instance of duplicate.txt (index 2)
./archive-alchemist.py archive.zip read duplicate.txt -i 2
```

## Notes and Warnings

- The `read` command outputs the file content to standard output (stdout). Binary files might produce unexpected results when printed directly to the terminal.

- When multiple entries have the same name, use the `--index` option to specify which instance to read. The index is zero-based, meaning `--index 0` refers to the first entry.

- For symlinks, the `read` command returns the symlink target path, not the content of the target file.