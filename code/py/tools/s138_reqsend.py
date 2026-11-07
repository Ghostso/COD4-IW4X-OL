#!/usr/bin/env python3
"""s138_reqsend: 找同一函数内 连续调用 [writeU32(0xB766B0)] [writeU32] [writeBool(0xB765E0)] 的构造器."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000 - VA, 0x401000 + 0x8a689a - VA

def callers(tgt):
    res = []; t = tgt - VA
    for i in range(TL, min(TH, N - 5)):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if (i + VA + 5 + rel) & 0xFFFFFFFF == tgt & 0xFFFFFFFF:
                res.append(i)
    return res

U32 = callers(0xB766B0)
BOOL = callers(0xB765E0)
print("u32 callers=%d bool callers=%d" % (len(U32), len(BOOL)))

# find u32..u32 within 60 bytes, and bool within 60 bytes after
import bisect
UB = sorted(U32)
for i in range(len(U32)):
    a = U32[i]
    # next u32 within 96
    nxt = [x for x in U32 if 0 < x - a <= 96]
    if not nxt:
        continue
    b = nxt[0]
    bl = [x for x in BOOL if -16 <= x - b <= 80]
    if bl:
        print("  construct @fn? u32@VA0x%08X u32@VA0x%08X bool@VA0x%08X" % (
            VA + a, VA + b, VA + bl[0]))
        # also check push 0x14 somewhere near
        seg = d[max(0, a - 60):b + 80]
        if b"\x6a\x14" in seg:
            print("      + contains push 0x14")
