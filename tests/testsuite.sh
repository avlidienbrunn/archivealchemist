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
    fi
  else
    echo -e "${RED}✗ Test failed: ${test_name} (command failed)${NC}"
  fi
  
  echo ""
}

# Clean up any existing test archives
cleanup() {
  echo "Cleaning up test archives..."
  rm -f test_*.zip test_*.tar test_*.tar.gz *.txt *.unknown *.tgz test_magic.*
  rm -rf test_extract
  rm -rf test_extract_*
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

# Test adding binary file to archive
run_test "Append - File with binary data" \
  "$ALCHEMIST -v -f test_append_binary.tar -t tar add original.txt --content '$(printf "c0ffee: \xc0\xff\xee")' && \
   mkdir -p test_append_binary && \
   $ALCHEMIST -v -f test_append_binary.tar -t tar extract --vulnerable --output-dir test_append_binary" \
  "[ -f test_append_binary/original.txt ] && \
   xxd -ps test_append_binary/original.txt | grep -q '6330666665653a20c0ffee'"

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