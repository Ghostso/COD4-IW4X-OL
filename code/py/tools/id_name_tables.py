#!/usr/bin/env python3
"""探测 {u32 id, u32 name_ptr} 记录数组。条件: 连续>=5 条, 每条 id 递增(允许跳),
ptr 指向可打印串。打印整表。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
DELTA = 0x714000
N = len(data)

def str_at_off(o):
    if not (0 <= o < N): return None
    e = data.find(b"\x00", o)
    if e < 0 or not (2 <= e - o <= 64): return None
    seg = data[o:e]
    if not all(32 <= c < 127 for c in seg): return None
    return seg.decode("ascii")

def rec_at(p):
    """返回 (id, name) 若 p 处是 {id, nameptr} 记录"""
    if p + 8 > N: return None
    idv, ptr = struct.unpack_from("<II", data, p)
    if not (0 <= idv <= 0x100000): return None
    o = ptr - DELTA
    s = str_at_off(o)
    if s is None: return None
    return (idv, s)

results = []
p = 0
while p + 8 <= N:
    r = rec_at(p)
    if r:
        # 尝试延展
        seq = [r]
        q = p + 8
        while q + 8 <= N:
            r2 = rec_at(q)
            if not r2: break
            if r2[0] <= seq[-1][0]:  # id 必须严格增
                break
            seq.append(r2)
            q += 8
        if len(seq) >= 5:
            results.append((p, seq))
            p = q
            continue
    p += 4

print("=== {id, name} 记录表 (>=5 条) ===")
for off, seq in results:
    print("\n--- @0x%06X  %d 条  id范围 %d..%d ---" % (off, len(seq), seq[0][0], seq[-1][0]))
    for idv, s in seq:
        print("   %6d  0x%04X  %r" % (idv, idv, s))
