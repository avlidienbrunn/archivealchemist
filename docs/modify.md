# Archive Alchemist: modify Command

## Overview

The `modify` command changes file attributes or converts files to symlinks/hardlinks without altering the content. This is useful for changing permissions, ownership, timestamps, or file types in an archive.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] modify <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive to modify (required) | N/A | `file.txt`, `bin/executable` |
| `--mode` | New file mode in octal notation | Current mode | `--mode 0755` |
| `--uid` | New User ID | Current UID | `--uid 0` |
| `--gid` | New Group ID | Current GID | `--gid 0` |
| `--mtime` | New modification time (Unix timestamp) | Current mtime | `--mtime 1609459200` |
| `--setuid` | Set the setuid bit | False | `--setuid` |
| `--setgid` | Set the setgid bit | False | `--setgid` |
| `--sticky` | Set the sticky bit | False | `--sticky` |
| `--symlink` | Convert file to a symlink pointing to this target | None | `--symlink "/etc/passwd"` |
| `--hardlink` | Convert file to a hardlink pointing to this target | None | `--hardlink "target.txt"` |

**Note**: At least one option must be specified to modify the file.

## Examples

### Changing File Permissions

```bash
# Make a file executable
./archive-alchemist.py archive.zip modify script.sh --mode 0755

# Remove write permissions
./archive-alchemist.py archive.tar -t tar modify sensitive.conf --mode 0444
```

### Changing Ownership

```bash
# Change ownership to root
./archive-alchemist.py archive.tar -t tar modify system.conf --uid 0 --gid 0

# Change only the group
./archive-alchemist.py archive.tar -t tar modify shared.txt --gid 100
```

### Setting Special Permission Bits

```bash
# Set the setuid bit
./archive-alchemist.py archive.tar -t tar modify bin/suid_exec --mode 0755 --setuid --uid 0

# Set the setgid bit
./archive-alchemist.py archive.tar -t tar modify shared/data --mode 0775 --setgid --gid 50

# Set the sticky bit
./archive-alchemist.py archive.tar -t tar modify tmp/ --mode 01777 --sticky
```

### Modifying Timestamps

```bash
# Set a specific modification time (January 1, 2021)
./archive-alchemist.py archive.zip modify old_file.txt --mtime 1609459200
```

### Converting Files to Symlinks

```bash
# Convert a regular file to a symlink
./archive-alchemist.py archive.tar -t tar modify config.ini --symlink "/etc/app/config.ini"

# Convert a file to a relative symlink
./archive-alchemist.py archive.zip modify link.txt --symlink "../target.txt"
```

### Converting Files to Hardlinks (TAR only)

```bash
# Convert a file to a hardlink
./archive-alchemist.py archive.tar -t tar modify copy.txt --hardlink "original.txt"
```

**Note**: ZIP format doesn't support true hardlinks. When converting to a hardlink in a ZIP file, Archive Alchemist creates a regular file with the target path as its content.

## Advanced Examples

### Security Testing with setuid

```bash
# Create a setuid root executable for privilege escalation testing
./archive-alchemist.py test.tar -t tar modify bin/exploit --mode 04755 --setuid --uid 0
```

### Backdooring an Archive

```bash
# Convert a legitimate config file to a symlink pointing to /etc/shadow
./archive-alchemist.py package.tar -t tar modify .bashrc --symlink "/etc/shadow"
```

### Manipulating Timestamps for Anti-Forensics

```bash
# Set an older timestamp to hide recent modifications
./archive-alchemist.py evidence.zip modify suspicious.log --mtime 1577836800  # Jan 1, 2020
```

## Notes and Warnings

- The `modify` command only changes file attributes or converts file types; it does not alter file content. To change content, use the `replace` or `append` commands.

- When converting a file to a symlink or hardlink, the original content is lost. Make sure you have a backup if needed.

- File permission and ownership attributes in ZIP files have limitations and may not be preserved by all ZIP utilities.

- While the setuid, setgid, and sticky bits can be set in both TAR and ZIP archives, they are only meaningful in Unix/Linux systems and may not be recognized by all extraction tools.

- When modifying TAR archives with compression (tar.gz, tar.xz, tar.bz2), the entire archive needs to be rewritten, which may take longer for large archives.

- Symlinks created in archives may be treated differently by various extraction tools. Some tools may refuse to extract symlinks that point outside the extraction directory for security reasons.