#!/usr/bin/env python3
"""s138_stride: 在 0x82C8800..0x82C9000 上暴力找最能解释为 [svc][task][arg] 的步长."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
SVC = {2,3,4,5,6,8,9,10,11,12,13,14,15,18,19}
lo, hi = 0x82C8800, 0x82C9400

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

best = None
for stride in (8, 12, 16, 20, 24, 28, 32, 36):
    for phase in range(0, stride, 4):
        start = lo + phase
        ok = 0; tot = 0; bad = []
        va = start
        while va + 8 <= hi:
            s = u32(va); t = u32(va + 4)
            tot += 1
            if s in SVC and 1 <= t <= 300:
                ok += 1
            else:
                bad.append(va)
            va += stride
        score = ok / tot if tot else 0
        if score > 0.85:
            if best is None or score > best[0]:
                best = (score, stride, phase, start, ok, tot, bad[:6])

if best:
    score, stride, phase, start, ok, tot, bad = best
    print("BEST stride=%d phase=%d start=0x%X score=%.3f (%d/%d) bad=%s" % (
        stride, phase, start, score, ok, tot, [hex(x) for x in bad]))
    va = start
    cnt = 0
    while va + 8 <= hi and cnt < 60:
        s = u32(va); t = u32(va + 4); a = u32(va + 8) if stride >= 12 else None
        print("  0x%08X: svc=%-3d task=%-3d arg=%s" % (va, s, t, a))
        va += stride; cnt += 1
else:
    print("no clean stride found")
