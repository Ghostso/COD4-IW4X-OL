#!/usr/bin/env python3
"""135 卷工具 F: 列出一个 VA 区间内所有 `E8 rel32` 直接调用目标(保序, 去重计数)."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr(va, maxlen=80):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


if __name__ == "__main__":
    lo = int(sys.argv[1], 0)
    hi = int(sys.argv[2], 0)
    i = lo - VA
    seq = []
    while i < hi - VA:
        if d[i] == 0xE8 and i + 5 <= N:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            tgt = VA + i + 5 + rel
            # 只收落在镜像内的
            if VA <= tgt < VA + N:
                seq.append((VA + i, tgt))
        i += 1
    from collections import Counter
    c = Counter(t for _, t in seq)
    print("区间 0x%08X..0x%08X : %d 个 E8 调用, %d 个不同目标" % (lo, hi, len(seq), len(c)))
    print()
    print("-- 出现顺序(不同目标) --")
    seen = set()
    for _, t in seq:
        if t in seen:
            continue
        seen.add(t)
        s = cstr(t)
        print("   0x%08X  x%-3d %s" % (t, c[t], ("'%s'" % s) if s else ""))
