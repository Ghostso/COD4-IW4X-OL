# -*- coding: utf-8 -*-
"""Dump hex+gbk+ascii around a file offset/range in a binary."""
import sys

path = sys.argv[1]
start = int(sys.argv[2], 0)
length = int(sys.argv[3], 0)

with open(path, "rb") as fh:
    fh.seek(start)
    blob = fh.read(length)

gbk = blob.decode("gbk", errors="replace")
print("---- GBK ----")
print(gbk)
print("---- ASCII (non-printable replaced by .) ----")
txt = "".join(chr(b) if 32 <= b < 127 else "." for b in blob)
print(txt)
