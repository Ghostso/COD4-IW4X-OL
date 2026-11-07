#!/usr/bin/env python3
"""s138_obj2_writers: for every caller of 0xB9A0F0 (returns singleton+0xD8),
scan the following window for stores/reads of [reg+0x20]/[reg+0x24].
Also group callers by code region.
Usage: python -I tools/s138_obj2_writers.py [window]
"""
import struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
T = 0xB9A0F0
WIN = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xC0


def entry_of(off):
    j = off
    while j > 1:
        if d[j - 1] == 0xCC and d[j - 2] == 0xCC:
            return VA + j
        j -= 1
    return None


sites = []
i = 0
while True:
    i = d.find(b"\xe8", i)
    if i < 0:
        break
    if i + 5 <= N:
        rel = struct.unpack_from("<i", d, i + 1)[0]
        if VA + i + 5 + rel == T:
            sites.append(i)
    i += 1

regions = {}
for s in sites:
    fn = entry_of(s) or 0
    regions.setdefault(fn >> 16, []).append((s, fn))
print("callers=%d" % len(sites))
for r in sorted(regions):
    fns = sorted(set(f for _, f in regions[r]))
    print("region 0x%02X0000: %d sites, %d funcs: %s" % (r, len(regions[r]),
          len(fns), [hex(x) for x in fns]))

print("\n--- stores/loads of +0x20 / +0x24 within %d bytes after call ---" % WIN)
for s, fn in sorted((s, fn) for s, _ in [(x, 0) for x in sites] for fn in [0]):
    pass
for s in sorted(sites):
    fn = entry_of(s) or 0
    code = d[s:s + WIN]
    for ins in md.disasm(code, VA + s):
        if ins.mnemonic in ("mov", "movzx", "movsx", "add", "cmp", "or", "test"):
            if re.search(r"\+ 0x2[04]\]", ins.op_str):
                print("  0x%08X [fn 0x%08X] %-8s %s" % (ins.address, fn, ins.mnemonic, ins.op_str))
