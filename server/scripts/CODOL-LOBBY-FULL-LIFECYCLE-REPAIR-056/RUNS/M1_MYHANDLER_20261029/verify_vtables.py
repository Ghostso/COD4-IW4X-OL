"""Verify vtable addresses against the E1 full-memory dump.

Dump layout: 2147352576 bytes == 0x7FFF0000 - 0x10000, so VA - 0x10000 = offset.

For each candidate vtable VA: dump the first 8 dwords (a real vtable holds code
pointers inside the image: 0x00401000..0x0EA59000) and count how many times the
address VALUE appears anywhere in the dump.
"""
import os
import struct
import sys

DUMP = r"run_codol_001\runs\E1_20261029_103001\dump\snap_002.bin"
BASE = 0x10000

VTS = {
    "dwroomimp (control)": 0x00DC7274,
    "dwroommatchuber": 0x00DC795C,
    "my_event_handler": 0x00DC78F0,
    "dwroommessage_text": 0x00DC7504,
}

IMG_LO, IMG_HI = 0x00401000, 0x0EA59000
f = open(DUMP, "rb")
size = os.path.getsize(DUMP)
print("dump size %d (0x%X)" % (size, size))

for name, va in VTS.items():
    off = va - BASE
    f.seek(off)
    raw = f.read(64)
    dwords = struct.unpack("<16I", raw)
    looks_like_vtable = all(IMG_LO <= d < IMG_HI for d in dwords[:4]) if dwords else False
    print("\n%s  VA=0x%08X" % (name, va))
    print("  first dwords: " + " ".join("%08X" % d for d in dwords[:8]))
    print("  looks_like_vtable(4 ptrs in image) = %s" % looks_like_vtable)

# count occurrences of each address value across the dump (chunked)
print("\n--- occurrence counts across whole dump ---")
needles = {name: struct.pack("<I", va) for name, va in VTS.items()}
counts = {name: 0 for name in VTS}
where = {name: [] for name in VTS}
CH = 1 << 24
f.seek(0)
pos = 0
overlap = b""
while True:
    buf = f.read(CH)
    if not buf:
        break
    data = overlap + buf
    base_off = pos - len(overlap)
    for name, needle in needles.items():
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            counts[name] += 1
            if len(where[name]) < 8:
                where[name].append(base_off + i + BASE)
            start = i + 1
    overlap = data[-4:]
    pos += len(buf)
for name in VTS:
    print("%-22s count=%d  first VAs=%s" % (
        name, counts[name], ["0x%08X" % w for w in where[name]]))
f.close()
