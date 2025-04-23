# Archive Alchemist: Supported Formats

## Supported Formats

| Format | Type Flag | File Extensions | Features | Limitations |
|--------|-----------|----------------|----------|-------------|
| ZIP | `zip` | `.zip` | Universal compatibility, widely supported | Limited Unix permissions, no true hardlinks |
| TAR | `tar` | `.tar` | Full Unix attributes, symlinks, hardlinks | No built-in compression, less widely supported on Windows |
| TAR.GZ | `tar.gz` | `.tar.gz`, `.tgz` | Compressed TAR with gzip | Not appendable, requires full rewrite for modifications |
| TAR.XZ | `tar.xz` | `.tar.xz`, `.txz` | Compressed TAR with xz | Not appendable, slower but better compression |
| TAR.BZ2 | `tar.bz2` | `.tar.bz2`, `.tbz2` | Compressed TAR with bzip2 | Not appendable, slower compression/decompression |

## Format Detection

Archive Alchemist can automatically detect the archive format in three ways:

1. **Explicit Type Flag**: Using the `-t` or `--type` option overrides any automatic detection.
   ```bash
   ./archive-alchemist.py -f archive.dat -t tar list
   ```

2. **Magic Bytes Detection**: For existing archives, the tool identifies the format by examining the file's content signature.
   ```bash
   # The tool will automatically detect this as a ZIP file regardless of extension
   ./archive-alchemist.py -f mysterious_file list
   ```

3. **Extension-based Detection**: For new archives or when magic bytes detection fails, the tool uses the file extension.
   ```bash
   # Will create a new TAR archive based on extension
   ./archive-alchemist.py -f new_archive.tar add file.txt --content "content"
   ```

For files with unrecognized extensions and no valid magic bytes, ZIP format is used by default.

## Magic Bytes Signatures

Archive Alchemist looks for these signatures when detecting file types:

- **ZIP**: Starts with `PK\x03\x04`
- **GZIP** (TAR.GZ): Starts with `\x1F\x8B`
- **XZ** (TAR.XZ): Starts with `\xFD\x37\x7A\x58\x5A\x00`
- **BZ2** (TAR.BZ2): Starts with `BZh`
- **TAR**: Detected by trying to open as a TAR file

## Format-Specific Behaviors

### Symlinks and Hardlinks

**ZIP:**
- Symlinks are supported using extension fields
- Hardlinks are simulated as regular files with the target path as content

**TAR and compressed TAR formats:**
- Native support for both symlinks and hardlinks
- Full preservation of link metadata

### Permission Bits

**ZIP:**
- Basic permissions (read/write/execute) are preserved
- Special bits (setuid, setgid, sticky) are stored but might not be recognized by all ZIP utilities

**TAR and compressed TAR formats:**
- Full preservation of all permission bits, including special bits