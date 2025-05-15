# Archive Alchemist: list Command

## Overview

The `list` (or the alias, `ls`) command displays the contents of an archive, showing all files, directories, symlinks, and hardlinks. It can show either a simple list of filenames or a detailed view with file attributes, similar to `ls -l` in Unix/Linux.

**NOTE**: Some zip utilities (such as unzip/zipinfo) will use the Unicode Path extra field for entry name/path. Archive Alchemist `-l1` (default) and `-l2` will display entry filename *and* this field. 

## Syntax

```bash
./archive-alchemist.py <archive> [-t <type>] list [options]
```

## Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--long`, `-l` | Show detailed listing with file attributes | 1 (True) | `--long 0` |
| `--longlong`, `-ll` | Show *very* detailed listing with file attribute/header information | 1 (True) | `--long 0` |

## Examples

## Output Format

### Simple Listing (--long 0)

```
Contents of archive.zip:
file.txt
directory/file2.txt
link.txt
```

### Detailed Listing (--long 1)

For ZIP archives, the detailed output includes:
```
Permissions  Size       Modified             Name
-rw-r--r--   12345      2023-06-15 10:30:45  file.txt
drwxr-xr-x   0          2023-06-15 10:30:00  directory/
lrwxrwxrwx   0          2023-06-15 10:31:15  link.txt -> target.txt
-rw-r--r--   12         2023-06-15 10:31:17  text.txt (unicode: text.txt)
```

For TAR archives, the detailed output includes:
```
Permissions  Owner/Group      Size       Modified             Name
-rw-r--r--   user/group       12345      2023-06-15 10:30:45  file.txt
drwxr-xr-x   user/group       0          2023-06-15 10:30:00  directory/
lrwxrwxrwx   user/group       0          2023-06-15 10:31:15  link.txt -> target.txt
-rwxr-xr-x   user/group       512        2023-06-15 10:32:00  hardlink.txt link to original.txt
```

### Detailed Listing (--long 2 or --longlong or -ll)

For ZIP archives, the detailed output includes:
```
Verbose header information for wowowo.zip:

File: passwd.txt
----------------------------------------------------------------------

  Local File Header (offset: 74):
    signature           : 504b0304
    version_needed      : 20
    flags               : 0 (none)
    compression_method  : 0 (stored (no compression))
    last_mod_time       : 0 (00:00:00)
    last_mod_date       : 33 (1980-01-01)
    crc_32              : 689944842
    compressed_size     : 11
    uncompressed_size   : 11
    filename_length     : 10
    extra_field_length  : 0
    filename            : passwd.txt

  Central Directory Header (offset: 204):
    signature           : 504b0102
    version_made_by     : 788
    version_needed      : 20
    flags               : 0 (none)
    compression_method  : 0 (stored (no compression))
    last_mod_time       : 0 (00:00:00)
    last_mod_date       : 33 (1980-01-01)
    crc_32              : 689944842
    compressed_size     : 11
    uncompressed_size   : 11
    filename_length     : 10
    extra_field_length  : 0
    comment_length      : 0
    disk_number_start   : 0
    internal_file_attr  : 0
    external_file_attr  : 2684354560 (Unix mode: 0o120000 l---------)
    local_header_offset : 74
    filename            : passwd.txt

  Header Field Comparison (CDH vs LFH):
    version_needed      : MATCH - CDH: 20, LFH: 20
    flags               : MATCH - CDH: 0, LFH: 0
    compression_method  : MATCH - CDH: 0, LFH: 0
    last_mod_time       : MATCH - CDH: 0, LFH: 0
    last_mod_date       : MATCH - CDH: 33, LFH: 33
    crc_32              : MATCH - CDH: 689944842, LFH: 689944842
    compressed_size     : MATCH - CDH: 11, LFH: 11
    uncompressed_size   : MATCH - CDH: 11, LFH: 11
    filename            : MATCH - CDH: passwd.txt, LFH: passwd.txt
----------------------------------------------------------------------

File: world.txt
----------------------------------------------------------------------

  Local File Header (offset: 0):
    signature           : 504b0304
    version_needed      : 20
    flags               : 0 (none)
    compression_method  : 8 (deflated)
    last_mod_time       : 3065 (01:31:50)
    last_mod_date       : 23192 (2025-04-24)
    crc_32              : 3760877631
    compressed_size     : 7
    uncompressed_size   : 8
    filename_length     : 9
    extra_field_length  : 28
    filename            : world.txt
    extra_hex           : 55 54 09 00 03 66 78 09 68 9e 78 09 68 75 78 0b 00 01 04 e8 03 00 00 04 e8 03 00 00
    extra_parsed        :
      UT_timestamp:
        mod_time: 1745451110 (2025-04-24 01:31:50)
        access_time: 1745451166 (2025-04-24 01:32:46)
      ux_uid_gid:
        version: 1
        uid: 1000
        gid: 1000

  Central Directory Header (offset: 125):
    signature           : 504b0102
    version_made_by     : 798
    version_needed      : 20
    flags               : 0 (none)
    compression_method  : 8 (deflated)
    last_mod_time       : 3065 (01:31:50)
    last_mod_date       : 23192 (2025-04-24)
    crc_32              : 3760877631
    compressed_size     : 7
    uncompressed_size   : 8
    filename_length     : 9
    extra_field_length  : 24
    comment_length      : 0
    disk_number_start   : 0
    internal_file_attr  : 1
    external_file_attr  : 2176057344 (Unix mode: 0o100664 -rw-rw-r--)
    local_header_offset : 0
    filename            : world.txt
    extra_hex           : 55 54 05 00 03 66 78 09 68 75 78 0b 00 01 04 e8 03 00 00 04 e8 03 00 00
    extra_parsed        :
      UT_timestamp:
        mod_time: 1745451110 (2025-04-24 01:31:50)
      ux_uid_gid:
        version: 1
        uid: 1000
        gid: 1000

  Header Field Comparison (CDH vs LFH):
    version_needed      : MATCH - CDH: 20, LFH: 20
    flags               : MATCH - CDH: 0, LFH: 0
    compression_method  : MATCH - CDH: 8, LFH: 8
    last_mod_time       : MATCH - CDH: 3065, LFH: 3065
    last_mod_date       : MATCH - CDH: 23192, LFH: 23192
    crc_32              : MATCH - CDH: 3760877631, LFH: 3760877631
    compressed_size     : MATCH - CDH: 7, LFH: 7
    uncompressed_size   : MATCH - CDH: 8, LFH: 8
    filename            : MATCH - CDH: world.txt, LFH: world.txt
----------------------------------------------------------------------
l---------         11  1980-01-01 00:00:00 passwd.txt -> /etc/passwd
-rw-rw-r--          8  2025-04-24 01:31:50 world.txt

```

For TAR archives, the detailed output includes:
```
File: ../hello.txt
----------------------------------------------------------------------
    name           : hello.txt
    mode           : 0o644 (-rw-r--r--)
    uid            : 1000
    gid            : 1000
    size           : 56
    mtime          : 1745452183 (2025-04-24 01:49:43)
    chksum         : 5802
    typeflag       : b'0' (regular file)
    linkname       : 
    magic          : ustar (USTAR format: Yes)
    version        : 00
    uname          : user
    gname          : group
    devmajor       : 0
    devminor       : 0
    prefix         : ..
    full_name      : ../hello.txt (constructed from prefix + name)
----------------------------------------------------------------------
File: linkme.txt
----------------------------------------------------------------------
    name           : linkme.txt
    mode           : 0o744 (-rwxr--r--)
    uid            : 0
    gid            : 0
    size           : 0
    mtime          : 0 (1970-01-01 01:00:00)
    chksum         : 5146
    typeflag       : b'2' (symbolic link)
    linkname       : /etc/passwd
    magic          : ustar (USTAR format: Yes)
    version        : 00
    uname          : 
    gname          : 
    devmajor       : 0
    devminor       : 0
    prefix         : 
----------------------------------------------------------------------
-rw-r--r-- user/group              56  2025-04-24 01:49:43 ../hello.txt
-rwxr--r-- 0/0                      0  1970-01-01 01:00:00 linkme.txt -> /etc/passwd
```

## Notes and Warnings

- The permissions shown in the detailed listing reflect what's stored in the archive, which may not match the permissions that will be applied when files are extracted. This is especially true for ZIP archives, where some utilities have limited support for preserving Unix permissions.

- For symlinks, the detailed listing shows the symlink target with `->` after the filename.

- For hardlinks (in TAR archives), the detailed listing shows the hardlink target with `link to` after the filename.

- Empty directories are included in the listing with a trailing slash (`/`).

- ZIP archives store timestamps with less precision than TAR archives (ZIP stores to the nearest 2 seconds), so the modification times shown might differ slightly from the original file times.

- For compressed archives (tar.gz, tar.xz, tar.bz2), the list command decompresses the archive in memory to read its contents, which may use more resources for large archives.