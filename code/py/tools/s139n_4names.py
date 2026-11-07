# -*- coding: utf-8 -*-
"""139n: 全镜像扫 push imm32 → 恰 4 字符 NUL 结尾可打印串。这些就是 srpc 服务名池。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000
N = len(d)

def c4(va):
    o = va - VA
    if not (0 <= o < N - 5):
        return None
    s = d[o:o + 4]
    if d[o + 4] != 0:
        return None
    if all(32 <= b < 127 for b in s):
        return s.decode()
    return None

hits = []
for i in range(0, N - 5):
    if d[i] == 0x68:
        imm = struct.unpack_from("<I", d, i + 1)[0]
        s = c4(imm)
        if s:
            hits.append((i + VA, imm, s))
print(f"push imm32 -> 4字符串: {len(hits)} 处")
seen = {}
for va, imm, s in hits:
    seen.setdefault(s, []).append(va)
for s in sorted(seen):
    print(f"  <{s}>  x{len(seen[s])}  @ {[hex(x) for x in seen[s][:6]]}")
