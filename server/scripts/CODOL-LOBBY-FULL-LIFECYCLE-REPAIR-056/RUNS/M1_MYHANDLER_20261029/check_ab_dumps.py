"""Decisive check of the 10-27 A/B claim.

Scan the memberCount=1 dump (EARLIEST2_20261027_132645) for the three vtable
values and classify each hit as image-far (VA < 0x10000000: .text/.rdata of the
EXE) or heap (VA >= 0x10000000: private allocations).

If dwroommatchuber really gained a heap instance when memberCount was 1, the
memberCount=1 dump must show a hit in the heap range.
"""
import os
import struct
import sys

BASE = 0x10000
VTS = {
    "dwroommatchuber": 0x00DC795C,
    "my_event_handler": 0x00DC78F0,
    "dwroomimp(control)": 0x00DC7274,
}
HEAP_LO = 0x10000000

runs = {
    "mc=1 snap_003": r"run_codol_001\runs\EARLIEST2_20261027_132645\snap_003.bin",
    "mc=1 snap_006": r"run_codol_001\runs\EARLIEST2_20261027_132645\snap_006.bin",
    "mc=0 snap_003": r"run_codol_001\runs\EARLIEST_20261027_123806\snap_003.bin",
}

needles = {k: struct.pack("<I", v) for k, v in VTS.items()}

for label, path in runs.items():
    if not os.path.isfile(path):
        print("%-16s MISSING %s" % (label, path))
        continue
    size = os.path.getsize(path)
    f = open(path, "rb")
    hits = {k: [] for k in VTS}
    CH = 1 << 24
    pos = 0
    overlap = b""
    while True:
        buf = f.read(CH)
        if not buf:
            break
        data = overlap + buf
        base_off = pos - len(overlap)
        for k, needle in needles.items():
            start = 0
            while True:
                i = data.find(needle, start)
                if i < 0:
                    break
                va = base_off + i + BASE
                if len(hits[k]) < 12:
                    hits[k].append(va)
                start = i + 1
        overlap = data[-4:]
        pos += len(buf)
    f.close()
    print("\n=== %s  (%d bytes) ===" % (label, size))
    for k in VTS:
        hs = hits[k]
        heap = [h for h in hs if h >= HEAP_LO]
        img = [h for h in hs if h < HEAP_LO]
        print("  %-20s total=%-3d image=%-3d heap=%-3d  %s" % (
            k, len(hs), len(img), len(heap),
            " ".join("0x%08X" % h for h in hs)))
