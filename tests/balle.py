import argparse
import sys
import re

parser = argparse.ArgumentParser(description="My awesome program")
parser.add_argument("--content", type=str, help="Some content with literal bytes")
args = parser.parse_args()

if args.content is not None:
    buffer = args.content.encode('utf-8', errors='surrogateescape')
    print(f"Processed bytes: {buffer}")
    print(f"Hex representation: {buffer.hex()}")