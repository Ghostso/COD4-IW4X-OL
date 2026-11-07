# -*- coding: utf-8 -*-
import struct, sys
sys.path.insert(0, "DEV-BOOKING/scripts")
BASE = 0x400000
IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG, "rb").read()
def find_va(n):
    i = d.find(n)
    return (BASE + i) if i >= 0 else None
targets = [b"mmstart sv_resetServer", b"MM_RESERVE_CMD_REQUEST Accepted",
           b"mmbook accepted", b"mmbook timedout", b"start_map_rotate_once", b"mmbook"]
for n in targets:
    va = find_va(n)
    if not va:
        print(n, "MISSING"); continue
    pat = struct.pack("<I", va)
    refs, s = [], 0
    while True:
        j = d.find(pat, s)
        if j < 0: break
        refs.append(BASE + j); s = j + 1
    print("%-34s VA=0x%08X  imm32 refs=%d  %s" % (n.decode(), va, len(refs),
          ", ".join("0x%08X" % x for x in refs[:14])))
    # pointer table? consecutive dwords in 0xDC6xxx range
    for x in refs[:4]:
        off = x - BASE
        around = struct.unpack_from("<8I", d, off - 12)
        print("      context @0x%08X : %s" % (x, " ".join("0x%08X" % w for w in around)))
