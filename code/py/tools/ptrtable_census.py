#!/usr/bin/env python3
"""通用指针表普查:
扫描全文件 u32 值 v, 若 v-DELTA 处是可打印 NUL 结尾串 => 记为字符串指针。
聚类(间距<=0x20)成表, 打印每表条目 (指针 -> 串) 以及相邻的 u32 数值(疑似 id)。
只打印条目数>=6 的表。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
DELTA = 0x714000
N = len(data)

# 预建: 所有字符串起始偏移 -> 串
def str_at_off(o):
    if not (0 <= o < N): return None
    e = data.find(b"\x00", o)
    if e < 0 or not (1 <= e - o <= 64): return None
    seg = data[o:e]
    if not all(32 <= c < 127 for c in seg): return None
    return seg.decode("ascii")

ptr_pos = []  # (file_pos, str)
for p in range(0, N - 4, 4):
    v = struct.unpack_from("<I", data, p)[0]
    o = v - DELTA
    if 0 <= o < N:
        s = str_at_off(o)
        if s is not None and len(s) >= 3:
            ptr_pos.append((p, s))

ptr_pos.sort()
# 聚类
clusters = []
cur = []
for p, s in ptr_pos:
    if cur and p - cur[-1][0] > 0x40:
        clusters.append(cur); cur = []
    cur.append((p, s))
if cur: clusters.append(cur)

print("=== 指针表 (>=6 条) ===")
for c in clusters:
    if len(c) < 6: continue
    print("\n--- table @0x%X .. 0x%X  (%d ptrs) ---" % (c[0][0], c[-1][0], len(c)))
    lo = c[0][0] - 8
    hi = c[-1][0] + 12
    p = lo
    while p + 4 <= hi:
        v = struct.unpack_from("<I", data, p)[0]
        o = v - DELTA
        s = str_at_off(o) if 0 <= o < N else None
        if s is not None and len(s) >= 3:
            print("   0x%06X: PTR %r" % (p, s))
        elif 0 < v < 0x100000:
            print("   0x%06X: 0x%08X (=%d)" % (p, v, v))
        else:
            print("   0x%06X: 0x%08X" % (p, v))
        p += 4
