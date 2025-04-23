#!/bin/bash
# Test suite for Archive Alchemist
# This script tests various features and verifies the results

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_TOTAL=0
TESTS_PASSED=0

# Function to run a test
run_test() {
  local test_name="$1"
  local command="$2"
  local verification="$3"
  
  echo -e "${YELLOW}Running test: ${test_name}${NC}"
  
  # Run the command
  eval "$command"
  local cmd_status=$?
  
  # Increment test counter
  TESTS_TOTAL=$((TESTS_TOTAL + 1))
  
  # Run verification
  if [ $cmd_status -eq 0 ]; then
    eval "$verification"
    local verify_status=$?
    
    if [ $verify_status -eq 0 ]; then
      echo -e "${GREEN}✓ Test passed: ${test_name}${NC}"
      TESTS_PASSED=$((TESTS_PASSED + 1))
    else
      echo -e "${RED}✗ Test failed: ${test_name} (verification failed)${NC}"
      exit 1
    fi
  else
    echo -e "${RED}✗ Test failed: ${test_name} (command failed)${NC}"
    exit 1
  fi
  
  echo ""
}

# Clean up any existing test archives
cleanup() {
  echo "Cleaning up test archives..."
  rm -f test_*.zip test_*.tar test_*.tar.gz *.txt *.unknown *.tgz *.bz2 *.xz *.txz *.tbz2 test_magic.*
  rm -rf test_extract
  rm -rf test_extract_*
  rm -rf test_dir_*
  rm -rf test_replace_*
  rm -rf test_empty_dirs
  mkdir -p test_extract
}

# Start with a clean slate
cleanup

# Path to the Archive Alchemist script
ALCHEMIST="../archive-alchemist.py"

run_test "ZIP - Add regular file" \
  "$ALCHEMIST -v -f test_regular.zip add hello.txt --content 'Hello, world!'" \
  "unzip -l test_regular.zip | grep -q 'hello.txt' && \
   unzip -p test_regular.zip hello.txt | grep -q 'Hello, world!'"

run_test "ZIP - Path traversal" \
  "$ALCHEMIST -v -f test_zipslip.zip add '../../../tmp/evil.txt' --content 'Path traversal'" \
  "unzip -l test_zipslip.zip | grep -q '../../../tmp/evil.txt'"

run_test "ZIP - Replace file" \
  "$ALCHEMIST -v -f test_replace.zip add file.txt --content 'Original' && \
   $ALCHEMIST -v -f test_replace.zip replace file.txt --content 'Replaced'" \
  "unzip -p test_replace.zip file.txt | grep -q 'Replaced' && \
   ! (unzip -p test_replace.zip file.txt | grep -q 'Original')"

run_test "ZIP - Append to file" \
  "$ALCHEMIST -v -f test_append.zip add file.txt --content 'Original' && \
   $ALCHEMIST -v -f test_append.zip append file.txt --content ' + Appended'" \
  "unzip -p test_append.zip file.txt | grep -q 'Original + Appended'"

run_test "ZIP - Symlink" \
  "$ALCHEMIST -v -f test_symlink.zip add link.txt --symlink '/etc/passwd'" \
  "unzip -l test_symlink.zip | grep -q 'link.txt'"

run_test "TAR - Add regular file" \
  "$ALCHEMIST -v -f test_regular.tar -t tar add hello.txt --content 'Hello, world!'" \
  "tar -tvf test_regular.tar | grep -q 'hello.txt' && \
   tar -xOf test_regular.tar hello.txt | grep -q 'Hello, world!'"

run_test "TAR - Symlink" \
  "$ALCHEMIST -v -f test_symlink.tar -t tar add link.txt --symlink '/etc/passwd'" \
  "tar -tvf test_symlink.tar | grep -q 'link.txt -> /etc/passwd'"

run_test "TAR - Setuid bit" \
  "$ALCHEMIST -v -f test_setuid.tar -t tar add exec.sh --content '#!/bin/sh\necho test' --mode 0755 --setuid" \
  "echo 'Archive contents:' && \
   [ \$(tar -tvf test_setuid.tar | grep 'exec.sh' | grep -c 'rws') -eq 1 ]"

run_test "TAR - UID/GID" \
  "$ALCHEMIST -v -f test_ids.tar -t tar add owned.txt --content 'Owned' --uid 1000 --gid 1000" \
  "tar -tvf test_ids.tar | grep -q 'owned.txt' && \
   tar -tvf test_ids.tar | grep -q '1000/1000'"

run_test "TAR.GZ - Compressed archive" \
  "$ALCHEMIST -v -f test_compressed.tar.gz -t tar.gz add hello.txt --content 'Compressed'" \
  "tar -tzvf test_compressed.tar.gz | grep -q 'hello.txt' && \
   tar -xzOf test_compressed.tar.gz hello.txt | grep -q 'Compressed'"

run_test "TAR - File collision with symlink" \
  "$ALCHEMIST -v -f test_collision.tar -t tar add config.txt --symlink '/tmp/target.txt' && \
   $ALCHEMIST -v -f test_collision.tar -t tar add config.txt --content 'Overwritten'" \
  "tar -tvf test_collision.tar | grep -q 'config.txt' && \
   tar -tvf test_collision.tar | grep -q -v 'config.txt -> /tmp/target.txt'"

run_test "TAR - Extract symlink behavior" \
  "$ALCHEMIST -v -f test_extract_symlink.tar -t tar add safe.txt --content 'Safe content' && \
   $ALCHEMIST -v -f test_extract_symlink.tar -t tar add evil.txt --symlink 'safe.txt' && \
   (cd test_extract && tar -xf ../test_extract_symlink.tar)" \
  "[ -L 'test_extract/evil.txt' ] && \
   LINK=\$(readlink 'test_extract/evil.txt') && \
   [ \"\$LINK\" = 'safe.txt' ] && \
   CONTENT=\$(cat 'test_extract/safe.txt') && \
   [ \"\$CONTENT\" = 'Safe content' ]"

run_test "TAR - Hardlink" \
  "$ALCHEMIST -v -f test_hardlink.tar -t tar add original.txt --content 'Original file content' && \
   $ALCHEMIST -v -f test_hardlink.tar -t tar add hardlink.txt --hardlink 'original.txt' && \
   (cd test_extract && tar -xf ../test_hardlink.tar)" \
  "[ -f 'test_extract/original.txt' ] && \
   [ -f 'test_extract/hardlink.txt' ] && \
   [ \$(tar -tvf test_hardlink.tar | grep -c 'hardlink.txt link to original.txt') -eq 1 ] && \
   CONTENT1=\$(cat 'test_extract/original.txt') && \
   CONTENT2=\$(cat 'test_extract/hardlink.txt') && \
   [ \"\$CONTENT1\" = \"\$CONTENT2\" ] && \
   [ \"\$CONTENT1\" = \"Original file content\" ]"

run_test "ZIP - Absolute path" \
  "$ALCHEMIST -v -f test_absolute_path.zip add '/tmp/absolute.txt' --content 'This file has an absolute path'" \
  "[ \$(unzip -l test_absolute_path.zip | grep -c '/tmp/absolute.txt') -eq 1 ] && \
   CONTENT=\$(unzip -p test_absolute_path.zip '/tmp/absolute.txt') && \
   [ \"\$CONTENT\" = \"This file has an absolute path\" ]"

run_test "Content File - Add from file" \
  "echo 'This content comes from a file' > test_source.txt && \
   $ALCHEMIST -v -f test_content_file.zip add doc.txt --content-file test_source.txt" \
  "CONTENT=\$(unzip -p test_content_file.zip doc.txt) && \
   [ \"\$CONTENT\" = \"This content comes from a file\" ]"

run_test "Content File - Replace with file" \
  "echo 'Original content' > test_replace_source.txt && \
   $ALCHEMIST -v -f test_replace_file.zip add original.txt --content 'Will be replaced' && \
   echo 'Replacement content' > test_replace_source.txt && \
   $ALCHEMIST -v -f test_replace_file.zip replace original.txt --content-file test_replace_source.txt" \
  "CONTENT=\$(unzip -p test_replace_file.zip original.txt) && \
   [ \"\$CONTENT\" = \"Replacement content\" ]"

run_test "Content File - Append from file" \
  "printf 'Original content' > test_orig.txt && \
   printf ' + appended from file' > test_append.txt && \
   $ALCHEMIST -v -f test_append_file.zip add append.txt --content-file test_orig.txt && \
   $ALCHEMIST -v -f test_append_file.zip append append.txt --content-file test_append.txt" \
  "unzip -p test_append_file.zip append.txt && \
   CONTENT=\$(unzip -p test_append_file.zip append.txt) && \
   echo \"Actual content: \$CONTENT\" && \
   [ \"\$CONTENT\" = \"Original content + appended from file\" ]"

run_test "Content File - Error on both options" \
  "echo 'Test content' > test_both.txt && \
   $ALCHEMIST -v -f test_both_error.zip add error.txt --content 'Direct content' --content-file test_both.txt" \
  "! [ -f test_both_error.zip ] || [ \$(unzip -l test_both_error.zip 2>/dev/null | grep -c 'error.txt') -eq 0 ]"

run_test "Content File - Error on missing file" \
  "$ALCHEMIST -v -f test_missing_file.zip add missing.txt --content-file non_existent_file.txt" \
  "! [ -f test_missing_file.zip ] || [ \$(unzip -l test_missing_file.zip 2>/dev/null | grep -c 'missing.txt') -eq 0 ]"

run_test "Remove - Single file from ZIP" \
  "$ALCHEMIST -v -f test_remove.zip add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_remove.zip add file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_remove.zip remove file1.txt" \
  "[ \$(unzip -l test_remove.zip | grep -c 'file1.txt') -eq 0 ] && \
   [ \$(unzip -l test_remove.zip | grep -c 'file2.txt') -eq 1 ]"

run_test "Remove - Directory from ZIP" \
  "$ALCHEMIST -v -f test_remove_dir.zip add dir/file1.txt --content 'Dir File 1' && \
   $ALCHEMIST -v -f test_remove_dir.zip add dir/file2.txt --content 'Dir File 2' && \
   $ALCHEMIST -v -f test_remove_dir.zip add outside.txt --content 'Outside' && \
   $ALCHEMIST -v -f test_remove_dir.zip remove dir" \
  "[ \$(unzip -l test_remove_dir.zip | grep -c 'dir/') -eq 0 ] && \
   [ \$(unzip -l test_remove_dir.zip | grep -c 'outside.txt') -eq 1 ]"

run_test "Remove - Single file from TAR" \
  "$ALCHEMIST -v -f test_remove.tar -t tar add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_remove.tar -t tar add file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_remove.tar -t tar remove file1.txt" \
  "[ \$(tar -tvf test_remove.tar | grep -c 'file1.txt') -eq 0 ] && \
   [ \$(tar -tvf test_remove.tar | grep -c 'file2.txt') -eq 1 ]"

run_test "Remove - Directory from TAR" \
  "$ALCHEMIST -v -f test_remove_dir.tar -t tar add dir/file1.txt --content 'Dir File 1' && \
   $ALCHEMIST -v -f test_remove_dir.tar -t tar add dir/file2.txt --content 'Dir File 2' && \
   $ALCHEMIST -v -f test_remove_dir.tar -t tar add outside.txt --content 'Outside' && \
   $ALCHEMIST -v -f test_remove_dir.tar -t tar remove dir" \
  "[ \$(tar -tvf test_remove_dir.tar | grep -c 'dir/') -eq 0 ] && \
   [ \$(tar -tvf test_remove_dir.tar | grep -c 'outside.txt') -eq 1 ]"

run_test "Remove - Non-existent file" \
  "$ALCHEMIST -v -f test_nonexistent.zip add file.txt --content 'Content' && \
   $ALCHEMIST -v -f test_nonexistent.zip remove nonexistent.txt 2>&1 | grep -q 'not found'" \
  "[ \$(unzip -l test_nonexistent.zip | grep -c 'file.txt') -eq 1 ]"

run_test "List - Simple ZIP listing" \
  "$ALCHEMIST -v -f test_list.zip add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_list.zip add file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_list.zip add dir/nested.txt --content 'Nested'" \
  "$ALCHEMIST -f test_list.zip list -l 0 | grep -q 'file1.txt' && \
   $ALCHEMIST -f test_list.zip list -l 0 | grep -q 'file2.txt' && \
   $ALCHEMIST -f test_list.zip list -l 0 | grep -q 'dir/nested.txt'"

run_test "List - Long ZIP listing" \
  "$ALCHEMIST -v -f test_list_long.zip add file.txt --content 'Regular file' --mode 0644 && \
   $ALCHEMIST -v -f test_list_long.zip add exec.sh --content '#!/bin/sh' --mode 0755 --setuid" \
  "$ALCHEMIST -f test_list_long.zip list -l 1 | grep -q 'file.txt' && \
   $ALCHEMIST -f test_list_long.zip list -l 1 | grep -q 'exec.sh' && \
   $ALCHEMIST -f test_list_long.zip list -l 1 | grep -q -- '-rw-r--r--' && \
   $ALCHEMIST -f test_list_long.zip list -l 1 | grep -q -- '-rwsr-xr-x'"

run_test "List - Simple TAR listing" \
  "$ALCHEMIST -v -f test_list.tar -t tar add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_list.tar -t tar add file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_list.tar -t tar add dir/nested.txt --content 'Nested'" \
  "$ALCHEMIST -f test_list.tar -t tar list -l 0 | grep -q 'file1.txt' && \
   $ALCHEMIST -f test_list.tar -t tar list -l 0 | grep -q 'file2.txt' && \
   $ALCHEMIST -f test_list.tar -t tar list -l 0 | grep -q 'dir/nested.txt'"

run_test "List - Long TAR listing" \
  "$ALCHEMIST -v -f test_list_long.tar -t tar add file.txt --content 'Regular file' --mode 0644 && \
   $ALCHEMIST -v -f test_list_long.tar -t tar add exec.sh --content '#!/bin/sh' --mode 0755 --setuid && \
   $ALCHEMIST -v -f test_list_long.tar -t tar add link.txt --symlink '/etc/passwd'" \
  "$ALCHEMIST -f test_list_long.tar -t tar list -l 1 | grep -q 'file.txt' && \
   $ALCHEMIST -f test_list_long.tar -t tar list -l 1 | grep -q 'exec.sh' && \
   $ALCHEMIST -f test_list_long.tar -t tar list -l 1 | grep -q 'link.txt -> /etc/passwd' && \
   $ALCHEMIST -f test_list_long.tar -t tar list -l 1 | grep -q -- '-rw-r--r--' && \
   $ALCHEMIST -f test_list_long.tar -t tar list -l 1 | grep -q -- '-rwsr-xr-x'"

run_test "List - Non-existent archive" \
  "true" \
  "$ALCHEMIST -f nonexistent.zip list 2>&1 | grep -q 'does not exist'"

run_test "Auto-detect - TAR type from filename" \
  "$ALCHEMIST -v -f test_autodetect.tar add file.txt --content 'TAR Content'" \
  "tar -tvf test_autodetect.tar | grep -q 'file.txt'"

run_test "Auto-detect - TAR.GZ type from filename" \
  "$ALCHEMIST -v -f test_autodetect.tar.gz add file.txt --content 'TAR.GZ Content'" \
  "tar -tzvf test_autodetect.tar.gz | grep -q 'file.txt'"

run_test "Auto-detect - TGZ type from filename" \
  "$ALCHEMIST -v -f test_autodetect.tgz add file.txt --content 'TGZ Content'" \
  "tar -tzvf test_autodetect.tgz | grep -q 'file.txt'"

run_test "Auto-detect - ZIP type from filename" \
  "$ALCHEMIST -v -f test_autodetect.zip add file.txt --content 'ZIP Content'" \
  "unzip -l test_autodetect.zip | grep -q 'file.txt'"

run_test "Auto-detect - Default to ZIP for unknown extension" \
  "$ALCHEMIST -v -f test_autodetect.unknown add file.txt --content 'Unknown Extension'" \
  "unzip -l test_autodetect.unknown | grep -q 'file.txt'"

run_test "Auto-detect - Override with explicit type flag" \
  "$ALCHEMIST -v -f test_override.tar -t zip add file.txt --content 'Overridden Type'" \
  "unzip -l test_override.tar | grep -q 'file.txt' && ! tar -tvf test_override.tar 2>/dev/null"

# Test for magic bytes detection
run_test "Magic Bytes - ZIP with wrong extension" \
  "$ALCHEMIST -v -f test_magic.zip add file.txt --content 'ZIP Content' && \
   cp test_magic.zip test_magic.wrongext" \
  "$ALCHEMIST -v -f test_magic.wrongext list 2>&1 | grep -q 'Auto-detected archive type: zip' && \
   unzip -l test_magic.wrongext | grep -q 'file.txt'"

run_test "Magic Bytes - TAR with wrong extension" \
  "$ALCHEMIST -v -f test_magic.tar -t tar add file.txt --content 'TAR Content' && \
   cp test_magic.tar test_magic.dat" \
  "$ALCHEMIST -v -f test_magic.dat list 2>&1 | grep -q 'Auto-detected archive type: tar' && \
   tar -tvf test_magic.dat | grep -q 'file.txt'"

run_test "Magic Bytes - TAR.GZ with wrong extension" \
  "$ALCHEMIST -v -f test_magic.tar.gz -t tar.gz add file.txt --content 'GZIP Content' && \
   cp test_magic.tar.gz test_magic.bin" \
  "$ALCHEMIST -v -f test_magic.bin list 2>&1 | grep -q 'Auto-detected archive type: tar.gz' && \
   tar -tzvf test_magic.bin | grep -q 'file.txt'"

run_test "Magic Bytes - Fallback to extension for new file" \
  "rm -f test_new_file.tar" \
  "$ALCHEMIST -v -f test_new_file.tar add file.txt --content 'New TAR' 2>&1 | grep -q 'Auto-detected archive type: tar' && \
   tar -tvf test_new_file.tar | grep -q 'file.txt'"


# Basic extraction test for ZIP
run_test "Extract - Basic ZIP extraction" \
  "$ALCHEMIST -v -f test_extract_basic.zip add file1.txt --content 'File 1 content' && \
   $ALCHEMIST -v -f test_extract_basic.zip add dir/file2.txt --content 'File 2 content' && \
   mkdir -p test_extract_basic && \
   $ALCHEMIST -v -f test_extract_basic.zip extract --output-dir test_extract_basic" \
  "[ -f test_extract_basic/file1.txt ] && \
   grep -q 'File 1 content' test_extract_basic/file1.txt && \
   [ -f test_extract_basic/dir/file2.txt ] && \
   grep -q 'File 2 content' test_extract_basic/dir/file2.txt"

# Test selective extraction
run_test "Extract - Selective extraction" \
  "$ALCHEMIST -v -f test_extract_selective.zip add file1.txt --content 'File 1 content' && \
   $ALCHEMIST -v -f test_extract_selective.zip add dir/file2.txt --content 'File 2 content' && \
   mkdir -p test_extract_selective && \
   $ALCHEMIST -v -f test_extract_selective.zip extract --path dir --output-dir test_extract_selective" \
  "[ ! -f test_extract_selective/file1.txt ] && \
   [ -f test_extract_selective/dir/file2.txt ] && \
   grep -q 'File 2 content' test_extract_selective/dir/file2.txt"

# Test safe mode (default) with path traversal
run_test "Extract - Safe mode path handling" \
  "$ALCHEMIST -v -f test_extract_safe.zip add ../outside.txt --content 'Outside content' && \
   $ALCHEMIST -v -f test_extract_safe.zip add /absolute/path.txt --content 'Absolute content' && \
   mkdir -p test_extract_safe && \
   $ALCHEMIST -v -f test_extract_safe.zip extract --output-dir test_extract_safe" \
  "[ ! -f test_extract_safe/../outside.txt ] && \
   [ -f test_extract_safe/outside.txt ] && \
   grep -q 'Outside content' test_extract_safe/outside.txt && \
   [ -f test_extract_safe/path.txt ] && \
   grep -q 'Absolute content' test_extract_safe/path.txt"

# Test symlink handling in safe mode
run_test "Extract - Safe mode symlink handling" \
  "$ALCHEMIST -v -f test_extract_safe_symlink.tar -t tar add target.txt --content 'Target content' && \
   $ALCHEMIST -v -f test_extract_safe_symlink.tar -t tar add link.txt --symlink target.txt && \
   mkdir -p test_extract_safe_symlink && \
   $ALCHEMIST -v -f test_extract_safe_symlink.tar -t tar extract --output-dir test_extract_safe_symlink" \
  "[ -f test_extract_safe_symlink/target.txt ] && \
   [ -f test_extract_safe_symlink/link.txt ] && \
   [ ! -L test_extract_safe_symlink/link.txt ] && \
   grep -q 'Target content' test_extract_safe_symlink/target.txt && \
   grep -q 'symlink to' test_extract_safe_symlink/link.txt"

# Test vulnerable mode with path traversal
run_test "Extract - Vulnerable mode path handling" \
  "mkdir -p test_extract_vuln && \
   $ALCHEMIST -v -f test_extract_vuln.zip add ../outside.txt --content 'Outside content' && \
   $ALCHEMIST -v -f test_extract_vuln.zip extract --vulnerable --output-dir test_extract_vuln" \
  "[ -f test_extract_vuln/../outside.txt ] && \
   grep -q 'Outside content' test_extract_vuln/../outside.txt" \
  || echo "Note: This test may fail if the parent directory isn't writable"

# Test symlink handling in vulnerable mode
run_test "Extract - Vulnerable mode symlink handling" \
  "$ALCHEMIST -v -f test_extract_vuln_symlink.tar -t tar add target.txt --content 'Target content' && \
   $ALCHEMIST -v -f test_extract_vuln_symlink.tar -t tar add link.txt --symlink target.txt && \
   mkdir -p test_extract_vuln_symlink && \
   $ALCHEMIST -v -f test_extract_vuln_symlink.tar -t tar extract --vulnerable --output-dir test_extract_vuln_symlink" \
  "[ -f test_extract_vuln_symlink/target.txt ] && \
   [ -L test_extract_vuln_symlink/link.txt ] && \
   LINK_TARGET=\$(readlink test_extract_vuln_symlink/link.txt) && \
   [ \"\$LINK_TARGET\" = \"target.txt\" ] && \
   grep -q 'Target content' test_extract_vuln_symlink/target.txt"

# Test for preserving permissions by default
run_test "Extract - Default preserve permissions" \
  "$ALCHEMIST -v -f test_extract_perms.tar -t tar add exec.sh --content '#!/bin/sh\necho test' --mode 0755 && \
   mkdir -p test_extract_perms && \
   $ALCHEMIST -v -f test_extract_perms.tar -t tar extract --output-dir test_extract_perms" \
  "[ -f test_extract_perms/exec.sh ] && \
   PERMS=\$(stat -c '%a' test_extract_perms/exec.sh) && \
   [ \"\$PERMS\" = \"755\" ]"

# Test for normalizing permissions
run_test "Extract - Normalize permissions" \
  "$ALCHEMIST -v -f test_extract_norm_perms.tar -t tar add exec.sh --content '#!/bin/sh\necho test' --mode 0755 && \
   mkdir -p test_extract_norm_perms && \
   $ALCHEMIST -v -f test_extract_norm_perms.tar -t tar extract --normalize-permissions --output-dir test_extract_norm_perms" \
  "[ -f test_extract_norm_perms/exec.sh ] && \
   PERMS=\$(stat -c '%a' test_extract_norm_perms/exec.sh) && \
   [ \"\$PERMS\" != \"755\" ]"

# Test TAR hardlinks in safe mode
run_test "Extract - Safe mode hardlinks" \
  "$ALCHEMIST -v -f test_extract_safe_hardlink.tar -t tar add original.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_extract_safe_hardlink.tar -t tar add hardlink.txt --hardlink original.txt && \
   mkdir -p test_extract_safe_hardlink && \
   $ALCHEMIST -v -f test_extract_safe_hardlink.tar -t tar extract --output-dir test_extract_safe_hardlink" \
  "[ -f test_extract_safe_hardlink/original.txt ] && \
   [ -f test_extract_safe_hardlink/hardlink.txt ] && \
   [ ! -L test_extract_safe_hardlink/hardlink.txt ] && \
   ORIG_INODE=\$(ls -i test_extract_safe_hardlink/original.txt | awk '{print \$1}') && \
   LINK_INODE=\$(ls -i test_extract_safe_hardlink/hardlink.txt | awk '{print \$1}') && \
   [ \"\$ORIG_INODE\" != \"\$LINK_INODE\" ] && \
   grep -q 'Original content' test_extract_safe_hardlink/original.txt"

# Test TAR hardlinks in vulnerable mode
run_test "Extract - Vulnerable mode hardlinks" \
  "$ALCHEMIST -v -f test_extract_vuln_hardlink.tar -t tar add original.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_extract_vuln_hardlink.tar -t tar add hardlink.txt --hardlink original.txt && \
   mkdir -p test_extract_vuln_hardlink && \
   $ALCHEMIST -v -f test_extract_vuln_hardlink.tar -t tar extract --vulnerable --output-dir test_extract_vuln_hardlink" \
  "[ -f test_extract_vuln_hardlink/original.txt ] && \
   [ -f test_extract_vuln_hardlink/hardlink.txt ] && \
   grep -q 'Original content' test_extract_vuln_hardlink/original.txt && \
   grep -q 'Original content' test_extract_vuln_hardlink/hardlink.txt"

# Test adding binary file content to archive
run_test "Append - File with binary data from arg" \
  "$ALCHEMIST -v -f test_extract_append_binary.tar -t tar add original.txt --content '$(printf "c0ffee: \xc0\xff\xee")' && \
   mkdir -p test_extract_append_binary && \
   $ALCHEMIST -v -f test_extract_append_binary.tar -t tar extract --vulnerable --output-dir test_extract_append_binary" \
  "[ -f test_extract_append_binary/original.txt ] && \
   xxd -ps test_extract_append_binary/original.txt | grep -q '6330666665653a20c0ffee'"

# Test adding binary file to archive
run_test "Append - File with binary data from file" \
  "printf 'c0ffee: \xc0\xff\xee' > binary-data.txt && \
   $ALCHEMIST -v -f test_extract_append_binary_fromfile.tar -t tar add original.txt --content-file binary-data.txt && \
   mkdir -p test_extract_append_binary_fromfile && \
   $ALCHEMIST -v -f test_extract_append_binary_fromfile.tar -t tar extract --vulnerable --output-dir test_extract_append_binary_fromfile" \
  "[ -f test_extract_append_binary_fromfile/original.txt ] && \
   xxd -ps test_extract_append_binary_fromfile/original.txt | grep -q '6330666665653a20c0ffee'"

# Test converting a regular file to a symlink in TAR
run_test "TAR - Modify file to symlink" \
  "$ALCHEMIST -v -f test_modify_to_symlink.tar -t tar add file.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_modify_to_symlink.tar -t tar modify file.txt --symlink '/etc/target'" \
  "tar -tvf test_modify_to_symlink.tar | grep -q 'file.txt -> /etc/target'"

# Test converting a regular file to a hardlink in TAR
run_test "TAR - Modify file to hardlink" \
  "$ALCHEMIST -v -f test_modify_to_hardlink.tar -t tar add original.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_modify_to_hardlink.tar -t tar add link.txt --content 'Will be replaced' && \
   $ALCHEMIST -v -f test_modify_to_hardlink.tar -t tar modify link.txt --hardlink 'original.txt'" \
  "tar -tvf test_modify_to_hardlink.tar | grep -q 'link.txt link to original.txt'"

# Test converting a regular file to a symlink in ZIP
run_test "ZIP - Modify file to symlink" \
  "$ALCHEMIST -v -f test_modify_to_symlink.zip add file.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_modify_to_symlink.zip modify file.txt --symlink '/etc/target'" \
  "unzip -v test_modify_to_symlink.zip | grep -q 'file.txt' && \
   [ \"\$(unzip -p test_modify_to_symlink.zip file.txt)\" = \"/etc/target\" ]"

# Test converting a regular file to a hardlink in ZIP (which doesn't natively support hardlinks)
run_test "ZIP - Modify file to hardlink (fallback to regular file)" \
  "$ALCHEMIST -v -f test_modify_to_hardlink.zip add original.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_modify_to_hardlink.zip add link.txt --content 'Will be replaced' && \
   $ALCHEMIST -v -f test_modify_to_hardlink.zip modify link.txt --hardlink 'original.txt'" \
  "unzip -v test_modify_to_hardlink.zip | grep -q 'link.txt' && \
   [ \"\$(unzip -p test_modify_to_hardlink.zip link.txt)\" = \"original.txt\" ]"

# Test extracting a file that was modified to be a symlink
run_test "Extract - Modified symlink extraction" \
  "$ALCHEMIST -v -f test_extract_modified_symlink.tar -t tar add target.txt --content 'Target content' && \
   $ALCHEMIST -v -f test_extract_modified_symlink.tar -t tar add file.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_extract_modified_symlink.tar -t tar modify file.txt --symlink 'target.txt' && \
   mkdir -p test_extract_modified_symlink && \
   $ALCHEMIST -v -f test_extract_modified_symlink.tar -t tar extract --vulnerable --output-dir test_extract_modified_symlink" \
  "[ -f test_extract_modified_symlink/target.txt ] && \
   [ -L test_extract_modified_symlink/file.txt ] && \
   LINK_TARGET=\$(readlink test_extract_modified_symlink/file.txt) && \
   [ \"\$LINK_TARGET\" = \"target.txt\" ] && \
   grep -q 'Target content' test_extract_modified_symlink/target.txt"

# Test with preserved mode bits when converting to symlink
run_test "TAR - Preserve mode bits when converting to symlink" \
  "$ALCHEMIST -v -f test_symlink_mode.tar -t tar add file.txt --content 'Original content' --mode 0755 && \
   $ALCHEMIST -v -f test_symlink_mode.tar -t tar modify file.txt --symlink '/etc/target' --mode 0777" \
  "tar -tvf test_symlink_mode.tar | grep -q 'file.txt -> /etc/target' && \
   [ \$(tar -tvf test_symlink_mode.tar | grep 'file.txt' | grep -c 'rwxrwxrwx') -eq 1 ]"

# Test for adding a directory structure - basic case
run_test "Directory - Add basic directory" \
  "mkdir -p test_dir_src/subdir && \
   echo 'File 1' > test_dir_src/file1.txt && \
   echo 'Subdir file' > test_dir_src/subdir/file2.txt && \
   $ALCHEMIST -v -f test_dir_add.zip add archive/ --content-directory test_dir_src" \
  "unzip -l test_dir_add.zip | grep -q 'archive/' && \
   unzip -l test_dir_add.zip | grep -q 'archive/file1.txt' && \
   unzip -l test_dir_add.zip | grep -q 'archive/subdir/' && \
   unzip -l test_dir_add.zip | grep -q 'archive/subdir/file2.txt' && \
   CONTENT1=\$(unzip -p test_dir_add.zip archive/file1.txt) && \
   [ \"\$CONTENT1\" = \"File 1\" ] && \
   CONTENT2=\$(unzip -p test_dir_add.zip archive/subdir/file2.txt) && \
   [ \"\$CONTENT2\" = \"Subdir file\" ]"

# Test for adding a directory structure to TAR
run_test "Directory - Add directory to TAR" \
  "mkdir -p test_dir_src_tar/subdir && \
   echo 'File 1' > test_dir_src_tar/file1.txt && \
   echo 'Subdir file' > test_dir_src_tar/subdir/file2.txt && \
   $ALCHEMIST -v -f test_dir_add.tar -t tar add archive/ --content-directory test_dir_src_tar" \
  "tar -tvf test_dir_add.tar | grep -q 'archive/' && \
   tar -tvf test_dir_add.tar | grep -q 'archive/file1.txt' && \
   tar -tvf test_dir_add.tar | grep -q 'archive/subdir/' && \
   tar -tvf test_dir_add.tar | grep -q 'archive/subdir/file2.txt' && \
   CONTENT1=\$(tar -xOf test_dir_add.tar archive/file1.txt) && \
   [ \"\$CONTENT1\" = \"File 1\" ] && \
   CONTENT2=\$(tar -xOf test_dir_add.tar archive/subdir/file2.txt) && \
   [ \"\$CONTENT2\" = \"Subdir file\" ]"

# Test for preserving empty directories
run_test "Directory - Preserve empty directories" \
  "mkdir -p test_empty_dirs/empty1 test_empty_dirs/empty2/empty3 && \
   echo 'Not empty' > test_empty_dirs/file.txt && \
   $ALCHEMIST -v -f test_empty_dirs.zip add root/ --content-directory test_empty_dirs" \
  "mkdir -p test_extract_empty && \
   unzip test_empty_dirs.zip -d test_extract_empty && \
   [ -d test_extract_empty/root/empty1 ] && \
   [ -d test_extract_empty/root/empty2/empty3 ]"

# Test for file symlinks
run_test "Directory - File symlinks" \
  "mkdir -p test_dir_symlinks && \
   echo 'Target file' > test_dir_symlinks/target.txt && \
   ln -sf target.txt test_dir_symlinks/link.txt && \
   $ALCHEMIST -v -f test_symlinks.zip add archive/ --content-directory test_dir_symlinks" \
  "unzip -l test_symlinks.zip | grep -q 'archive/target.txt' && \
   unzip -l test_symlinks.zip | grep -q 'archive/link.txt' && \
   content=\$(unzip -p test_symlinks.zip archive/link.txt) && \
   [ \"\$content\" = \"target.txt\" ]"

# Test for directory symlinks
run_test "Directory - Directory symlinks" \
  "mkdir -p test_dir_symlinks2/real_dir && \
   echo 'File in real dir' > test_dir_symlinks2/real_dir/file.txt && \
   ln -sf real_dir test_dir_symlinks2/link_dir && \
   $ALCHEMIST -v -f test_dir_symlinks.tar -t tar add archive/ --content-directory test_dir_symlinks2" \
  "tar -tvf test_dir_symlinks.tar | grep -q 'archive/real_dir/' && \
   tar -tvf test_dir_symlinks.tar | grep -q 'archive/real_dir/file.txt' && \
   tar -tvf test_dir_symlinks.tar | grep -q 'archive/link_dir -> real_dir'"

# Test with mode and owner attributes
run_test "Directory - With attributes" \
  "mkdir -p test_dir_attrs/subdir && \
   echo 'File with attributes' > test_dir_attrs/file.txt && \
   $ALCHEMIST -v -f test_dir_attrs.tar -t tar add archive/ --content-directory test_dir_attrs --mode 0755 --uid 1000 --gid 1000" \
  "tar -tvf test_dir_attrs.tar | grep 'archive/file.txt' | grep -q '1000/1000' && \
   tar -tvf test_dir_attrs.tar | grep 'archive/file.txt' | grep -q 'rwxr-xr-x'"

# Test extraction of added directory
run_test "Directory - Extract added directory" \
  "mkdir -p test_dir_extract/subdir && \
   echo 'File 1' > test_dir_extract/file1.txt && \
   echo 'Subdir file' > test_dir_extract/subdir/file2.txt && \
   $ALCHEMIST -v -f test_dir_extract.zip add archive/ --content-directory test_dir_extract && \
   mkdir -p test_extract_dir && \
   $ALCHEMIST -v -f test_dir_extract.zip extract --output-dir test_extract_dir" \
  "[ -f test_extract_dir/archive/file1.txt ] && \
   [ -f test_extract_dir/archive/subdir/file2.txt ] && \
   CONTENT1=\$(cat test_extract_dir/archive/file1.txt) && \
   [ \"\$CONTENT1\" = \"File 1\" ] && \
   CONTENT2=\$(cat test_extract_dir/archive/subdir/file2.txt) && \
   [ \"\$CONTENT2\" = \"Subdir file\" ]"

# Test for overriding file permissions with --mode
run_test "Directory - Override file permissions with --mode" \
  "rm -f test_override.tar && \
   mkdir -p test_dir_override && \
   echo 'Regular file' > test_dir_override/regular.txt && \
   echo 'Will be executable' > test_dir_override/make_exec.txt && \
   chmod 0644 test_dir_override/regular.txt && \
   chmod 0644 test_dir_override/make_exec.txt && \
   $ALCHEMIST -v -f test_override.tar -t tar add archive/ --content-directory test_dir_override --mode 0755" \
  "tar -tvf test_override.tar | grep 'archive/regular.txt' | grep -q 'rwxr-xr-x' && \
   tar -tvf test_override.tar | grep 'archive/make_exec.txt' | grep -q 'rwxr-xr-x'"

# Test for preserving file permissions
run_test "Directory - Preserve file permissions" \
  "rm -f test_perms.tar && \
   mkdir -p test_dir_perms && \
   echo 'Regular file' > test_dir_perms/regular.txt && \
   echo 'Executable file' > test_dir_perms/exec.sh && \
   chmod 0644 test_dir_perms/regular.txt && \
   chmod 0755 test_dir_perms/exec.sh && \
   $ALCHEMIST -v -f test_perms.tar -t tar add archive/ --content-directory test_dir_perms" \
  "tar -tvf test_perms.tar | grep 'archive/regular.txt' | grep -q 'rw-r--r--' && \
   tar -tvf test_perms.tar | grep 'archive/exec.sh' | grep -q 'rwxr-xr-x'"

# Test for preserving directory permissions
run_test "Directory - Preserve directory permissions" \
  "rm -f test_dirperms.tar && \
   mkdir -p test_dir_dirperms/normal_dir test_dir_dirperms/special_dir && \
   chmod 0755 test_dir_dirperms/normal_dir && \
   chmod 0770 test_dir_dirperms/special_dir && \
   $ALCHEMIST -v -f test_dirperms.tar -t tar add archive/ --content-directory test_dir_dirperms && \
   echo 'TAR contents:' && \
   tar -tvf test_dirperms.tar" \
  "tar -tvf test_dirperms.tar | grep 'archive/normal_dir/' | grep -q -- 'rwxr-xr-x' && \
   tar -tvf test_dirperms.tar | grep 'archive/special_dir/' | grep -q -- 'rwxrwx---'"

# Test for preserving permissions in ZIP archives
run_test "Directory - Preserve permissions in ZIP" \
  "rm -f test_zip_perms.zip && \
   mkdir -p test_dir_zip_perms && \
   echo 'Regular file' > test_dir_zip_perms/regular.txt && \
   echo 'Executable file' > test_dir_zip_perms/exec.sh && \
   chmod 0644 test_dir_zip_perms/regular.txt && \
   chmod 0755 test_dir_zip_perms/exec.sh && \
   $ALCHEMIST -v -f test_zip_perms.zip add archive/ --content-directory test_dir_zip_perms && \
   mkdir -p test_extract_zip_perms && \
   unzip test_zip_perms.zip -d test_extract_zip_perms" \
  "[ \$(stat -c '%a' test_extract_zip_perms/archive/regular.txt) = '644' ] && \
   [ \$(stat -c '%a' test_extract_zip_perms/archive/exec.sh) = '755' ]"

# Test for overwriting existing files with --content-directory
run_test "Directory - Overwrite existing files" \
  "rm -f test_overwrite.zip && \
   # First add some initial files
   $ALCHEMIST -v -f test_overwrite.zip add archive/file1.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_overwrite.zip add archive/file2.txt --content 'Will be replaced' && \
   # Now create local directory with modified files
   mkdir -p test_dir_overwrite && \
   echo 'Updated content' > test_dir_overwrite/file1.txt && \
   echo 'New file' > test_dir_overwrite/file3.txt && \
   # Add directory which should update existing files
   $ALCHEMIST -v -f test_overwrite.zip add archive/ --content-directory test_dir_overwrite" \
  "unzip -l test_overwrite.zip | grep -q 'archive/file1.txt' && \
   unzip -l test_overwrite.zip | grep -q 'archive/file2.txt' && \
   unzip -l test_overwrite.zip | grep -q 'archive/file3.txt' && \
   CONTENT1=\$(unzip -p test_overwrite.zip archive/file1.txt) && \
   [ \"\$CONTENT1\" = \"Updated content\" ] && \
   CONTENT2=\$(unzip -p test_overwrite.zip archive/file2.txt) && \
   [ \"\$CONTENT2\" = \"Will be replaced\" ] && \
   CONTENT3=\$(unzip -p test_overwrite.zip archive/file3.txt) && \
   [ \"\$CONTENT3\" = \"New file\" ]"

# Test for overwriting a file with a symlink
run_test "Directory - Overwrite file with symlink" \
  "rm -f test_overwrite_symlink.tar && \
   # First add a regular file
   $ALCHEMIST -v -f test_overwrite_symlink.tar -t tar add archive/target.txt --content 'Target content' && \
   $ALCHEMIST -v -f test_overwrite_symlink.tar -t tar add archive/regular.txt --content 'Will be a symlink' && \
   # Now create directory with a symlink
   mkdir -p test_dir_overwrite_symlink && \
   echo 'Target file' > test_dir_overwrite_symlink/target.txt && \
   ln -sf target.txt test_dir_overwrite_symlink/regular.txt && \
   # Add directory which should update the file to a symlink
   $ALCHEMIST -v -f test_overwrite_symlink.tar -t tar add archive/ --content-directory test_dir_overwrite_symlink" \
  "tar -tvf test_overwrite_symlink.tar | grep -q 'archive/target.txt' && \
   tar -tvf test_overwrite_symlink.tar | grep -q 'archive/regular.txt -> target.txt'"

# Test for overwriting with updated permissions
run_test "Directory - Overwrite with updated permissions" \
  "rm -f test_overwrite_perms.tar && \
   # First add a file with basic permissions
   $ALCHEMIST -v -f test_overwrite_perms.tar -t tar add archive/script.sh --content '#!/bin/sh\necho test' --mode 0644 && \
   # Now create directory with executable file
   mkdir -p test_dir_overwrite_perms && \
   echo '#!/bin/sh\necho updated' > test_dir_overwrite_perms/script.sh && \
   chmod 0755 test_dir_overwrite_perms/script.sh && \
   # Add directory which should update permissions
   $ALCHEMIST -v -f test_overwrite_perms.tar -t tar add archive/ --content-directory test_dir_overwrite_perms" \
  "tar -tvf test_overwrite_perms.tar | grep 'archive/script.sh' | grep -q 'rwxr-xr-x' && \
   CONTENT=\$(tar -xOf test_overwrite_perms.tar archive/script.sh) && \
   [ \"\$CONTENT\" = \"#!/bin/sh\necho updated\" ]"

# Test for overwriting in nested directory structure
run_test "Directory - Overwrite in nested structure" \
  "rm -f test_overwrite_nested.zip && \
   # First add nested structure
   $ALCHEMIST -v -f test_overwrite_nested.zip add archive/dir1/file.txt --content 'Original' && \
   $ALCHEMIST -v -f test_overwrite_nested.zip add archive/dir2/file.txt --content 'Not changed' && \
   # Now create directory with modified nested structure
   mkdir -p test_dir_overwrite_nested/dir1 && \
   echo 'Updated' > test_dir_overwrite_nested/dir1/file.txt && \
   mkdir -p test_dir_overwrite_nested/dir3 && \
   echo 'New directory' > test_dir_overwrite_nested/dir3/file.txt && \
   # Add directory which should update files in dir1 and add dir3
   $ALCHEMIST -v -f test_overwrite_nested.zip add archive/ --content-directory test_dir_overwrite_nested" \
  "unzip -l test_overwrite_nested.zip | grep -q 'archive/dir1/file.txt' && \
   unzip -l test_overwrite_nested.zip | grep -q 'archive/dir2/file.txt' && \
   unzip -l test_overwrite_nested.zip | grep -q 'archive/dir3/file.txt' && \
   CONTENT1=\$(unzip -p test_overwrite_nested.zip archive/dir1/file.txt) && \
   [ \"\$CONTENT1\" = \"Updated\" ] && \
   CONTENT2=\$(unzip -p test_overwrite_nested.zip archive/dir2/file.txt) && \
   [ \"\$CONTENT2\" = \"Not changed\" ] && \
   CONTENT3=\$(unzip -p test_overwrite_nested.zip archive/dir3/file.txt) && \
   [ \"\$CONTENT3\" = \"New directory\" ]"

# Test replace with --content
run_test "Replace - With content" \
  "rm -f test_replace_content.zip && \
   $ALCHEMIST -v -f test_replace_content.zip add file.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_replace_content.zip replace file.txt --content 'Replaced content'" \
  "unzip -p test_replace_content.zip file.txt | grep -q 'Replaced content' && \
   ! (unzip -p test_replace_content.zip file.txt | grep -q 'Original content')"

# Test replace with --content-file
run_test "Replace - With content-file" \
  "rm -f test_replace_content_file.zip && \
   $ALCHEMIST -v -f test_replace_content_file.zip add file.txt --content 'Original content' && \
   echo 'Replaced from file' > test_replace_source.txt && \
   $ALCHEMIST -v -f test_replace_content_file.zip replace file.txt --content-file test_replace_source.txt" \
  "unzip -p test_replace_content_file.zip file.txt | grep -q 'Replaced from file' && \
   ! (unzip -p test_replace_content_file.zip file.txt | grep -q 'Original content')"

# Test replace with --content-directory (single file)
run_test "Replace - With content-directory (single file)" \
  "rm -f test_replace_dir_single.zip && \
   $ALCHEMIST -v -f test_replace_dir_single.zip add archive/file.txt --content 'Original content' && \
   mkdir -p test_replace_dir_src && \
   echo 'Replaced via directory' > test_replace_dir_src/file.txt && \
   $ALCHEMIST -v -f test_replace_dir_single.zip replace archive/ --content-directory test_replace_dir_src" \
  "unzip -p test_replace_dir_single.zip archive/file.txt | grep -q 'Replaced via directory'"

# Test replace with --content-directory (multiple files)
run_test "Replace - With content-directory (multiple files)" \
  "rm -f test_replace_dir_multi.zip && \
   $ALCHEMIST -v -f test_replace_dir_multi.zip add archive/file1.txt --content 'Original 1' && \
   $ALCHEMIST -v -f test_replace_dir_multi.zip add archive/file2.txt --content 'Original 2' && \
   $ALCHEMIST -v -f test_replace_dir_multi.zip add other/file.txt --content 'Not replaced' && \
   mkdir -p test_replace_dir_multi_src && \
   echo 'Replaced 1' > test_replace_dir_multi_src/file1.txt && \
   echo 'Replaced 2' > test_replace_dir_multi_src/file2.txt && \
   echo 'New file' > test_replace_dir_multi_src/file3.txt && \
   $ALCHEMIST -v -f test_replace_dir_multi.zip replace archive/ --content-directory test_replace_dir_multi_src" \
  "unzip -p test_replace_dir_multi.zip archive/file1.txt | grep -q 'Replaced 1' && \
   unzip -p test_replace_dir_multi.zip archive/file2.txt | grep -q 'Replaced 2' && \
   unzip -p test_replace_dir_multi.zip archive/file3.txt | grep -q 'New file' && \
   unzip -p test_replace_dir_multi.zip other/file.txt | grep -q 'Not replaced'"

# Test replace with symlink
run_test "Replace - With symlink" \
  "rm -f test_replace_symlink.tar && \
   $ALCHEMIST -v -f test_replace_symlink.tar -t tar add file.txt --content 'Original content' && \
   $ALCHEMIST -v -f test_replace_symlink.tar -t tar replace file.txt --symlink '/etc/passwd'" \
  "tar -tvf test_replace_symlink.tar | grep -q 'file.txt -> /etc/passwd'"

# Test replace with hardlink
run_test "Replace - With hardlink" \
  "rm -f test_replace_hardlink.tar && \
   $ALCHEMIST -v -f test_replace_hardlink.tar -t tar add original.txt --content 'Target content' && \
   $ALCHEMIST -v -f test_replace_hardlink.tar -t tar add link.txt --content 'Will be a hardlink' && \
   $ALCHEMIST -v -f test_replace_hardlink.tar -t tar replace link.txt --hardlink 'original.txt'" \
  "tar -tvf test_replace_hardlink.tar | grep -q 'link.txt link to original.txt'"

# Test replace with modified attributes
run_test "Replace - With modified attributes" \
  "rm -f test_replace_attrs.tar && \
   $ALCHEMIST -v -f test_replace_attrs.tar -t tar add file.txt --content 'Normal file' --mode 0644 && \
   $ALCHEMIST -v -f test_replace_attrs.tar -t tar replace file.txt --content 'Executable file' --mode 0755 --setuid" \
  "tar -tvf test_replace_attrs.tar | grep -q 'file.txt' && \
   tar -tvf test_replace_attrs.tar | grep -q 'rws' && \
   tar -xOf test_replace_attrs.tar file.txt | grep -q 'Executable file'"

# Test replace in ZIP with modified attributes
run_test "Replace - ZIP with modified attributes" \
  "rm -f test_replace_zip_attrs.zip && \
   $ALCHEMIST -v -f test_replace_zip_attrs.zip add file.txt --content 'Normal file' --mode 0644 && \
   $ALCHEMIST -v -f test_replace_zip_attrs.zip replace file.txt --content 'Executable file' --mode 0755 && \
   mkdir -p test_extract_replace_attrs && \
   unzip test_replace_zip_attrs.zip -d test_extract_replace_attrs" \
  "[ -f test_extract_replace_attrs/file.txt ] && \
   [ \$(stat -c '%a' test_extract_replace_attrs/file.txt) = '755' ] && \
   grep -q 'Executable file' test_extract_replace_attrs/file.txt"

# Test replace directory (ensure old files are removed)
run_test "Replace - Directory with complete replacement" \
  "rm -f test_replace_dir_complete.zip && \
   # First add a directory with some files
   $ALCHEMIST -v -f test_replace_dir_complete.zip add archive/file1.txt --content 'Original file 1' && \
   $ALCHEMIST -v -f test_replace_dir_complete.zip add archive/file2.txt --content 'Original file 2' && \
   $ALCHEMIST -v -f test_replace_dir_complete.zip add archive/subdir/file3.txt --content 'Original file 3' && \
   # Now create a new directory with different files
   mkdir -p test_replace_dir_new/newdir && \
   echo 'New content' > test_replace_dir_new/new_file.txt && \
   echo 'New subdir file' > test_replace_dir_new/newdir/file.txt && \
   # Replace the directory
   $ALCHEMIST -v -f test_replace_dir_complete.zip replace archive/ --content-directory test_replace_dir_new" \
  "# Verify new files exist
   unzip -l test_replace_dir_complete.zip | grep -q 'archive/new_file.txt' && \
   unzip -l test_replace_dir_complete.zip | grep -q 'archive/newdir/file.txt' && \
   # Verify old files don't exist
   ! (unzip -l test_replace_dir_complete.zip | grep -q 'archive/file1.txt') && \
   ! (unzip -l test_replace_dir_complete.zip | grep -q 'archive/file2.txt') && \
   ! (unzip -l test_replace_dir_complete.zip | grep -q 'archive/subdir/file3.txt')"

# Test non-recursive remove with --recursive 0
run_test "Remove - Non-recursive directory removal" \
  "rm -f test_nonrecursive_remove.zip && \
   # First add a directory with some files
   $ALCHEMIST -v -f test_nonrecursive_remove.zip add dir/file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_nonrecursive_remove.zip add dir/file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_nonrecursive_remove.zip add dir/subdir/file3.txt --content 'File 3' && \
   # Now remove just the directory entry but not its contents
   $ALCHEMIST -v -f test_nonrecursive_remove.zip remove dir/ --recursive 0" \
  "# Verify directory entry is removed
   ! (unzip -l test_nonrecursive_remove.zip | grep -q 'dir/$') && \
   # Verify files still exist
   unzip -l test_nonrecursive_remove.zip | grep -q 'dir/file1.txt' && \
   unzip -l test_nonrecursive_remove.zip | grep -q 'dir/file2.txt' && \
   unzip -l test_nonrecursive_remove.zip | grep -q 'dir/subdir/file3.txt'"

# Test recursive remove (default behavior)
run_test "Remove - Default recursive directory removal" \
  "rm -f test_recursive_remove.zip && \
   # First add a directory with some files
   $ALCHEMIST -v -f test_recursive_remove.zip add dir/file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_recursive_remove.zip add dir/file2.txt --content 'File 2' && \
   $ALCHEMIST -v -f test_recursive_remove.zip add dir/subdir/file3.txt --content 'File 3' && \
   $ALCHEMIST -v -f test_recursive_remove.zip add outside.txt --content 'Outside' && \
   # Now remove the directory with default recursive behavior
   $ALCHEMIST -v -f test_recursive_remove.zip remove dir/" \
  "# Verify directory and contents are removed
   ! (unzip -l test_recursive_remove.zip | grep -q 'dir/') && \
   # Verify outside file still exists
   unzip -l test_recursive_remove.zip | grep -q 'outside.txt'"

# Test for creating a basic tar.xz archive
run_test "TAR.XZ - Add regular file" \
  "rm -f test_regular.tar.xz && \
   $ALCHEMIST -v -f test_regular.tar.xz -t tar.xz add hello.txt --content 'Hello, XZ compression!' && \
   tar -tJf test_regular.tar.xz | grep -q 'hello.txt'" \
  "tar -xJOf test_regular.tar.xz hello.txt | grep -q 'Hello, XZ compression!'"

# Test for creating a basic tar.bz2 archive
run_test "TAR.BZ2 - Add regular file" \
  "rm -f test_regular.tar.bz2 && \
   $ALCHEMIST -v -f test_regular.tar.bz2 -t tar.bz2 add hello.txt --content 'Hello, BZ2 compression!' && \
   tar -tjf test_regular.tar.bz2 | grep -q 'hello.txt'" \
  "tar -xjOf test_regular.tar.bz2 hello.txt | grep -q 'Hello, BZ2 compression!'"

# Test format auto-detection from filename
run_test "Format detection - tar.xz from filename" \
  "rm -f test_detection.tar.xz && \
   $ALCHEMIST -v -f test_detection.tar.xz add hello.txt --content 'Auto-detected XZ'" \
  "tar -tJf test_detection.tar.xz | grep -q 'hello.txt' && \
   tar -xJOf test_detection.tar.xz hello.txt | grep -q 'Auto-detected XZ'"

# Test format auto-detection from filename
run_test "Format detection - tar.bz2 from filename" \
  "rm -f test_detection.tar.bz2 && \
   $ALCHEMIST -v -f test_detection.tar.bz2 add hello.txt --content 'Auto-detected BZ2'" \
  "tar -tjf test_detection.tar.bz2 | grep -q 'hello.txt' && \
   tar -xjOf test_detection.tar.bz2 hello.txt | grep -q 'Auto-detected BZ2'"

# Test for short filename variants (.txz, .tbz2)
run_test "Format detection - .txz extension" \
  "rm -f test_detection.txz && \
   $ALCHEMIST -v -f test_detection.txz add hello.txt --content 'TXZ file'" \
  "tar -tJf test_detection.txz | grep -q 'hello.txt' && \
   tar -xJOf test_detection.txz hello.txt | grep -q 'TXZ file'"

run_test "Format detection - .tbz2 extension" \
  "rm -f test_detection.tbz2 && \
   $ALCHEMIST -v -f test_detection.tbz2 add hello.txt --content 'TBZ2 file'" \
  "tar -tjf test_detection.tbz2 | grep -q 'hello.txt' && \
   tar -xjOf test_detection.tbz2 hello.txt | grep -q 'TBZ2 file'"

# Test listing for tar.xz
run_test "TAR.XZ - List contents" \
  "rm -f test_list.tar.xz && \
   $ALCHEMIST -v -f test_list.tar.xz -t tar.xz add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_list.tar.xz -t tar.xz add file2.txt --content 'File 2'" \
  "$ALCHEMIST -f test_list.tar.xz list | grep -q 'file1.txt' && \
   $ALCHEMIST -f test_list.tar.xz list | grep -q 'file2.txt'"

# Test listing for tar.bz2
run_test "TAR.BZ2 - List contents" \
  "rm -f test_list.tar.bz2 && \
   $ALCHEMIST -v -f test_list.tar.bz2 -t tar.bz2 add file1.txt --content 'File 1' && \
   $ALCHEMIST -v -f test_list.tar.bz2 -t tar.bz2 add file2.txt --content 'File 2'" \
  "$ALCHEMIST -f test_list.tar.bz2 list | grep -q 'file1.txt' && \
   $ALCHEMIST -f test_list.tar.bz2 list | grep -q 'file2.txt'"

# Test extraction for tar.xz
run_test "TAR.XZ - Extract files" \
  "rm -f test_extract.tar.xz && \
   rm -rf test_extract_xz && \
   mkdir -p test_extract_xz && \
   $ALCHEMIST -v -f test_extract.tar.xz -t tar.xz add file1.txt --content 'XZ File 1' && \
   $ALCHEMIST -v -f test_extract.tar.xz -t tar.xz add file2.txt --content 'XZ File 2' && \
   $ALCHEMIST -v -f test_extract.tar.xz extract --output-dir test_extract_xz" \
  "[ -f test_extract_xz/file1.txt ] && \
   [ -f test_extract_xz/file2.txt ] && \
   grep -q 'XZ File 1' test_extract_xz/file1.txt && \
   grep -q 'XZ File 2' test_extract_xz/file2.txt"

# Test extraction for tar.bz2
run_test "TAR.BZ2 - Extract files" \
  "rm -f test_extract.tar.bz2 && \
   rm -rf test_extract_bz2 && \
   mkdir -p test_extract_bz2 && \
   $ALCHEMIST -v -f test_extract.tar.bz2 -t tar.bz2 add file1.txt --content 'BZ2 File 1' && \
   $ALCHEMIST -v -f test_extract.tar.bz2 -t tar.bz2 add file2.txt --content 'BZ2 File 2' && \
   $ALCHEMIST -v -f test_extract.tar.bz2 extract --output-dir test_extract_bz2" \
  "[ -f test_extract_bz2/file1.txt ] && \
   [ -f test_extract_bz2/file2.txt ] && \
   grep -q 'BZ2 File 1' test_extract_bz2/file1.txt && \
   grep -q 'BZ2 File 2' test_extract_bz2/file2.txt"

# Test magic bytes detection for tar.xz
run_test "Magic bytes - tar.xz" \
  "rm -f test_magic.tar.xz && \
   $ALCHEMIST -v -f test_magic.tar.xz -t tar.xz add file.txt --content 'XZ Content' && \
   cp test_magic.tar.xz test_magic.bin" \
  "$ALCHEMIST -v -f test_magic.bin list 2>&1 | grep -q 'Auto-detected archive type: tar.xz' && \
   tar -tJf test_magic.bin | grep -q 'file.txt'"

# Test magic bytes detection for tar.bz2
run_test "Magic bytes - tar.bz2" \
  "rm -f test_magic.tar.bz2 && \
   $ALCHEMIST -v -f test_magic.tar.bz2 -t tar.bz2 add file.txt --content 'BZ2 Content' && \
   cp test_magic.tar.bz2 test_magic.dat" \
  "$ALCHEMIST -v -f test_magic.dat list 2>&1 | grep -q 'Auto-detected archive type: tar.bz2' && \
   tar -tjf test_magic.dat | grep -q 'file.txt'"

# Print summary
echo -e "${YELLOW}Test Summary: ${TESTS_PASSED}/${TESTS_TOTAL} tests passed${NC}"
if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
  echo -e "${GREEN}All tests passed!${NC}"
else
  echo -e "${RED}Some tests failed.${NC}"
  exit 1
fi

# Cleanup
cleanup