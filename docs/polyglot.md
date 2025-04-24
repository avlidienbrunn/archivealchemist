# Archive Alchemist: polyglot Command

## Overview

The `polyglot` command prepends content to an archive while maintaining the archive's validity (adjusts offsets in ZIP and ensures 512 block size for TAR).

## Syntax

```bash
./archive-alchemist.py -f <archive> [-t <type>] polyglot [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--content` | Text content to prepend to the archive | Empty | `--content "HTTP/1.1 200 OK\r\n\r\n"` |
| `--content-file` | Path to a local file whose content should be prepended | None | `--content-file /path/to/header.bin` |

**Note**: You must specify either `--content` or `--content-file`.

## How It Works

For ZIP archives:
- Prepends the specified content to the beginning of the file
- Adjusts all local file header offsets in the central directory
- Adjusts the central directory offset in the end of central directory record

For TAR archives:
- Prepends the specified content to the beginning of the file
- Adds padding with null bytes to maintain proper 512-byte block alignment

## Examples

### Basic Usage

```bash
# Prepend text content to a ZIP file
./archive-alchemist.py -f archive.zip polyglot --content "PREPENDED_CONTENT"

# Prepend content from a file to a TAR archive
./archive-alchemist.py -f archive.tar -t tar polyglot --content-file header.bin
```

## Notes and Warnings

- No ZIP64 support, ie might cause problems for archives larger than 4 GB