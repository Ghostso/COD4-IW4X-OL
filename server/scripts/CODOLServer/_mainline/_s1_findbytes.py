# -*- coding: utf-8 -*-
"""Recursively search files for an ASCII or GBK needle and print file+offset."""
import os
import sys

root = sys.argv[1]
mode = sys.argv[2]  # ascii | gbk | hex
needle = sys.argv[3]

if mode == "ascii":
    pat = needle.encode("latin-1")
elif mode == "gbk":
    pat = needle.encode("gbk")
else:
    pat = bytes.fromhex(needle)

skip_ext = {
    ".etl", ".pcapng", ".pcap", ".dmp", ".bin", ".pak", ".tvm0",
    ".zip", ".7z", ".rar", ".exe", ".dll", ".dat", ".tlg", ".ff",
}

hits = 0
for dirpath, _dirnames, filenames in os.walk(root):
    for name in filenames:
        path = os.path.join(dirpath, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > 400 * 1024 * 1024:
            continue
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError:
            continue
        start = 0
        while True:
            i = blob.find(pat, start)
            if i < 0:
                break
            print("%s off=0x%08X" % (path, i))
            hits += 1
            start = i + 1
            if hits > 200:
                print("... (truncated)")
                sys.exit(0)
print("total", hits)
