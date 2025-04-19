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
  rm -f test_*.zip test_*.tar test_*.tar.gz
  rm -rf test_extract
  mkdir -p test_extract
}

# Start with a clean slate
cleanup

# Path to the Archive Alchemist script
ALCHEMIST="../archive-alchemist.py"

# Test 1: Create a ZIP file with a regular file
run_test "ZIP - Add regular file" \
  "$ALCHEMIST -v -f test_regular.zip add hello.txt --content 'Hello, world!'" \
  "unzip -l test_regular.zip | grep -q 'hello.txt' && \
   unzip -p test_regular.zip hello.txt | grep -q 'Hello, world!'"

# Test 2: Create a ZIP file with path traversal
run_test "ZIP - Path traversal" \
  "$ALCHEMIST -v -f test_zipslip.zip add '../../../tmp/evil.txt' --content 'Path traversal'" \
  "unzip -l test_zipslip.zip | grep -q '../../../tmp/evil.txt'"

# Test 3: Replace a file in a ZIP archive
run_test "ZIP - Replace file" \
  "$ALCHEMIST -v -f test_replace.zip add file.txt --content 'Original' && \
   $ALCHEMIST -v -f test_replace.zip replace file.txt --content 'Replaced'" \
  "unzip -p test_replace.zip file.txt | grep -q 'Replaced' && \
   ! (unzip -p test_replace.zip file.txt | grep -q 'Original')"

# Test 4: Append to a file in a ZIP archive
run_test "ZIP - Append to file" \
  "$ALCHEMIST -v -f test_append.zip add file.txt --content 'Original' && \
   $ALCHEMIST -v -f test_append.zip append file.txt --content ' + Appended'" \
  "unzip -p test_append.zip file.txt | grep -q 'Original + Appended'"

# Test 5: Create a symlink in a ZIP file (modern format)
run_test "ZIP - Symlink" \
  "$ALCHEMIST -v -f test_symlink.zip add link.txt --symlink '/etc/passwd'" \
  "unzip -l test_symlink.zip | grep -q 'link.txt'"

# Test 6: Create a TAR file with a regular file
run_test "TAR - Add regular file" \
  "$ALCHEMIST -v -f test_regular.tar -t tar add hello.txt --content 'Hello, world!'" \
  "tar -tvf test_regular.tar | grep -q 'hello.txt' && \
   tar -xOf test_regular.tar hello.txt | grep -q 'Hello, world!'"

# Test 7: Create a TAR file with a symlink
run_test "TAR - Symlink" \
  "$ALCHEMIST -v -f test_symlink.tar -t tar add link.txt --symlink '/etc/passwd'" \
  "tar -tvf test_symlink.tar | grep -q 'link.txt -> /etc/passwd'"

# Test 8: Create a TAR file with setuid bit
run_test "TAR - Setuid bit" \
  "$ALCHEMIST -v -f test_setuid.tar -t tar add exec.sh --content '#!/bin/sh\necho test' --mode 0755 --setuid" \
  "echo 'Archive contents:' && \
   [ \$(tar -tvf test_setuid.tar | grep 'exec.sh' | grep -c 'rws') -eq 1 ]"

# Test 9: Create a TAR file with specific uid/gid
run_test "TAR - UID/GID" \
  "$ALCHEMIST -v -f test_ids.tar -t tar add owned.txt --content 'Owned' --uid 1000 --gid 1000" \
  "tar -tvf test_ids.tar | grep -q 'owned.txt' && \
   tar -tvf test_ids.tar | grep -q '1000/1000'"

# Test 10: Create a compressed TAR.GZ file
run_test "TAR.GZ - Compressed archive" \
  "$ALCHEMIST -v -f test_compressed.tar.gz -t tar.gz add hello.txt --content 'Compressed'" \
  "tar -tzvf test_compressed.tar.gz | grep -q 'hello.txt' && \
   tar -xzOf test_compressed.tar.gz hello.txt | grep -q 'Compressed'"

# Test 11: File collision with symlink in TAR
run_test "TAR - File collision with symlink" \
  "$ALCHEMIST -v -f test_collision.tar -t tar add config.txt --symlink '/tmp/target.txt' && \
   $ALCHEMIST -v -f test_collision.tar -t tar add config.txt --content 'Overwritten'" \
  "tar -tvf test_collision.tar | grep -q 'config.txt' && \
   tar -tvf test_collision.tar | grep -q -v 'config.txt -> /tmp/target.txt'"

# Test 12: Verify symlink extraction behavior
run_test "TAR - Extract symlink behavior" \
  "$ALCHEMIST -v -f test_extract_symlink.tar -t tar add safe.txt --content 'Safe content' && \
   $ALCHEMIST -v -f test_extract_symlink.tar -t tar add evil.txt --symlink 'safe.txt' && \
   (cd test_extract && tar -xf ../test_extract_symlink.tar)" \
  "[ -L 'test_extract/evil.txt' ] && \
   LINK=\$(readlink 'test_extract/evil.txt') && \
   [ \"\$LINK\" = 'safe.txt' ] && \
   CONTENT=\$(cat 'test_extract/safe.txt') && \
   [ \"\$CONTENT\" = 'Safe content' ]"

# Test 13: Verify hardlink in tar
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

# Test 14: Absolute path in ZIP
run_test "ZIP - Absolute path" \
  "$ALCHEMIST -v -f test_absolute_path.zip add '/tmp/absolute.txt' --content 'This file has an absolute path'" \
  "[ \$(unzip -l test_absolute_path.zip | grep -c '/tmp/absolute.txt') -eq 1 ] && \
   CONTENT=\$(unzip -p test_absolute_path.zip '/tmp/absolute.txt') && \
   [ \"\$CONTENT\" = \"This file has an absolute path\" ]"

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