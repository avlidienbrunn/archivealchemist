# Archive Alchemist: extract Command

## Overview

The `extract` command extracts files from an archive to the filesystem. By default, it operates in a safe mode that prevents path traversal attacks, blocks absolute paths, and converts symlinks to regular files. It also offers a vulnerable mode for security testing that allows potentially unsafe extractions.

## Syntax

```bash
./archive-alchemist.py -f <archive> [-t <type>] extract [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--path` | Path within the archive to extract (default: extract all) | None | `--path some/dir` |
| `--output-dir`, `-o` | Directory to extract files to | `.` (current directory) | `--output-dir /path/to/extract` |
| `--vulnerable` | Allow potentially unsafe extractions | False | `--vulnerable` |
| `--normalize-permissions` | Normalize file permissions during extraction | False | `--normalize-permissions` |

## Examples

### Basic Extraction

```bash
# Extract all files from an archive to the current directory
./archive-alchemist.py -f archive.zip extract

# Extract to a specific directory
./archive-alchemist.py -f archive.tar -t tar extract --output-dir /path/to/extract
```

### Selective Extraction

```bash
# Extract a specific file
./archive-alchemist.py -f archive.zip extract --path file.txt

# Extract a specific directory and its contents
./archive-alchemist.py -f archive.zip extract --path some/dir
```

### Safe Mode Extraction (Default)

The default safe mode provides the following protections:

```bash
# Path traversal prevention (runs in safe mode by default)
./archive-alchemist.py -f suspicious.zip extract --output-dir /path/to/safe

# Symlinks are converted to regular files with information about the target
./archive-alchemist.py -f symlinks.tar -t tar extract --output-dir /path/to/safe
```

### Vulnerable Mode Extraction

```bash
# Allow path traversal and other potentially unsafe extractions
./archive-alchemist.py -f malicious.zip extract --vulnerable --output-dir /path/to/test

# Extract with actual symlinks instead of converting them to regular files
./archive-alchemist.py -f symlinks.tar -t tar extract --vulnerable --output-dir /path/to/test
```

### Permission Handling

```bash
# Preserve original permissions (default behavior)
./archive-alchemist.py -f archive.tar -t tar extract --output-dir /path/to/extract

# Normalize permissions instead of preserving them
./archive-alchemist.py -f archive.tar -t tar extract --normalize-permissions --output-dir /path/to/extract
```

## Advanced Examples

### Creating a Test Environment for Path Traversal

```bash
# Create a ZIP with path traversal
./archive-alchemist.py -f zipslip.zip add "../../../tmp/evil.txt" --content "I escaped!"

# Test extraction in vulnerable mode to observe the behavior
./archive-alchemist.py -f zipslip.zip extract --vulnerable --output-dir /path/to/test
```

### Testing Symlink Attacks

```bash
# Create a TAR with a symlink pointing to a sensitive file
./archive-alchemist.py -f symlink_attack.tar -t tar add configs/passwd --symlink "/etc/passwd"

# Extract in vulnerable mode to test how symlinks are handled
./archive-alchemist.py -f symlink_attack.tar -t tar extract --vulnerable --output-dir /path/to/test
```

### Analyzing Permission-Based Attacks

```bash
# Create archive with setuid executable
./archive-alchemist.py -f setuid_test.tar -t tar add exploit --content "#!/bin/sh\nwhoami" --mode 4755 --setuid --uid 0

# Extract and see how permissions are handled
./archive-alchemist.py -f setuid_test.tar -t tar extract --output-dir /path/to/test
```

## Safe Mode Features

When extracting without the `--vulnerable` flag (default), Archive Alchemist provides several security features:

1. **Path Traversal Prevention**: Paths containing `../` or starting with `/` are sanitized to prevent directory traversal attacks.

2. **Symlink Safety**: Symlinks are converted to regular text files containing information about the symlink target.

3. **Hardlink Safety**: Hardlinks are converted to regular text files with information about the original target.

4. **Permission Preservation**: By default, file permissions are preserved, but permissions can be normalized with `--normalize-permissions`.

## Vulnerable Mode

When extracting with the `--vulnerable` flag, Archive Alchemist disables safety features to allow security testing:

1. **Path Traversal Allowed**: Files can be extracted outside the target directory using `../` or absolute paths.

2. **Symlinks Preserved**: Actual symlinks are created pointing to their original targets.

3. **Hardlinks Preserved**: Actual hardlinks are created when possible.

## Notes and Warnings

- Using `--vulnerable` allows potentially dangerous operations and should be used only in controlled testing environments.

- For compressed archives (tar.gz, tar.xz, tar.bz2), the extraction process includes decompression, which may take longer for large archives.

- The `--normalize-permissions` flag can help prevent permission-based attacks by ignoring the permissions stored in the archive.