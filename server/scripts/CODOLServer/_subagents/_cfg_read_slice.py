#!/usr/bin/env python3
"""Print a byte/line slice of a text file. ASCII-only script.

Usage: python _cfg_read_slice.py <path> <start_line> <count>
"""

import sys
from pathlib import Path


def main():
    path = Path(sys.argv[1])
    start = int(sys.argv[2])
    count = int(sys.argv[3])
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    for index in range(start, min(start + count, len(lines))):
        sys.stdout.buffer.write(lines[index].encode("utf-8", "replace"))
        sys.stdout.buffer.write(b"\n")
    print("--- total_lines=%d ---" % len(lines))


if __name__ == "__main__":
    main()
