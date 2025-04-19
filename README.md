# Archive Alchemist

Archive Alchemist is a security research tool for creating specially crafted archives to test extraction vulnerabilities. 100% vibecoded, use at own disposal.

## Features

- Create ZIP and TAR archives with malicious patterns
- Support for path traversal attacks
- Support for symlinks and hardlinks
- Ability to set special permission bits (setuid, setgid, sticky bit)
- Fine-grained control over file attributes (mode, uid, gid, mtime)
- Multiple manipulation commands: add, replace, append, modify

## Installation

```bash
# Clone the repository
git clone https://github.com/avlidienbrunn/archive-alchemist.git
cd archive-alchemist

# Make the script executable
chmod +x archive-alchemist.py

# Optional: create a symlink to use globally
sudo ln -s $(pwd)/archive-alchemist.py /usr/local/bin/archive-alchemist
```

## Usage

### Basic Usage

```bash
./archive-alchemist.py -f archive.zip -t zip <command> [options]
```

### Archive Type Detection

If `-t`/`--type` flag is not specified, Archive Alchemist determines the archive type in two ways:

1. **Magic Bytes Detection**: For existing archives, the tool identifies the format by examining the file's content signature.

2. **Extension-based Detection**: For new archives or when magic bytes detection fails, the tool uses the file extension:
   - `.zip`: ZIP format
   - `.tar`: TAR format
   - `.tar.gz` or `.tgz`: Compressed TAR format

For files with unrecognized extensions and no valid magic bytes, ZIP format is used by default.

You can always override automatic detection by explicitly specifying the `-t` flag:

```bash
# Force TAR format regardless of extension or content:
./archive-alchemist.py -f archive.zip -t tar add file.txt --content "Using TAR format"
```

### Commands

#### Add Files

```bash
# Add a regular file
./archive-alchemist.py -f archive.zip add hello.js --content "console.log('hello')"

# Add a file with path traversal
./archive-alchemist.py -f archive.tar -t tar add "../../../etc/passwd" --content "fake passwd file"

# Add a symlink
./archive-alchemist.py -f archive.tar -t tar add hello.js --symlink "/tmp/xx.txt"

# Add with permission bits
./archive-alchemist.py -f archive.tar -t tar add exploit.sh --content "#!/bin/sh\necho hacked" --mode 0755 --setuid
```

#### Replace Files

```bash
# Replace existing file content
./archive-alchemist.py -f archive.zip replace hello.js --content "console.log('replaced')"
```

#### Append to Files

```bash
# Append content to existing file
./archive-alchemist.py -f archive.zip append hello.js --content "\nconsole.log('appended')"
```

#### Modify Attributes

```bash
# Modify file attributes
./archive-alchemist.py -f archive.tar -t tar modify hello.js --mode 0755 --uid 0 --gid 0 --setuid
```

#### Remove Files

```bash
# Remove a file from an archive
./archive-alchemist.py -v -f archive.zip remove file.txt

# Remove a directory and all its contents
./archive-alchemist.py -v -f archive.tar -t tar remove directory/
```

#### List Archive Contents

```bash
# List files in an archive
./archive-alchemist.py -f archive.zip list

# Show detailed listing with file attributes
./archive-alchemist.py -f archive.tar -t tar list --long 1

# or the short form
./archive-alchemist.py -f archive.zip list -l 0
```

### Examples for Security Testing

#### Zip Slip Attack

```bash
# Create a zip with path traversal payload
./archive-alchemist.py -f zipslip.zip add "../../../tmp/evil.txt" --content "I escaped the extraction directory!"
```

#### Symlink Attack

```bash
# Create a tar with a symlink pointing to a sensitive file
./archive-alchemist.py -f symlink_attack.tar -t tar add .bashrc --symlink "/etc/passwd"
```

#### File Collisions with Symlinks

```bash
# First add a symlink
./archive-alchemist.py -f collision.tar -t tar add config.txt --symlink "/tmp/target.txt"

# Then add a regular file with the same name (will be extracted last)
./archive-alchemist.py -f collision.tar -t tar add config.txt --content "Overwrite after symlink is created"
```

#### Setuid Executable

```bash
# Create a setuid executable
./archive-alchemist.py -f setuid_attack.tar -t tar add exploit --content "#!/bin/sh\nwhoami" --mode 0755 --setuid --uid 0
```

## Security Considerations

This tool is designed for security research and vulnerability testing. Using it against systems without explicit permission is illegal and unethical.