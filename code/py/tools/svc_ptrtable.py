#!/usr/bin/env python3
"""找指向服务名串的指针数组。给出串 -> VA, 在文件里搜 4 字节 LE 指针, 打印相邻指针组。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000

# 候选服务名串偏移 (来自 svc_region 转储)
names = {
    "storage.check": 0x6CCB4C, "canceled": 0x6CCB5C, "timeout": 0x6CCB68,
    "pending": 0x6CCB70, "reward": 0x6CCB78, "titleutilities": 0x6CCB80,
    "tencent": 0x6CCB90, "teams": 0x6CCB98, "storage": 0x6CCBA0,
    "profiles": 0x6CCBA8, "pooledstorage": 0x6CCBB4, "messaging": 0x6CCBC4,
    "matchmaking": 0x6CCBD0, "marketplace": 0x6CCBDC, "eventlog": 0x6CCBE8,
    "non_critical": 0x6CCBF4, "critical": 0x6CCC04,
}

def find_ptr(va):
    ptr = struct.pack("<I", va + BASE)
    out = []
    i = 0
    while True:
        p = data.find(ptr, i)
        if p < 0:
            return out
        out.append(p)
        i = p + 1

print("=== 每个串的 VA 指针出现位置 ===")
hits = {}
for n, off in names.items():
    ps = find_ptr(off)
    hits[n] = ps
    print("  %-16s off=0x%X  ptrs=%s" % (n, off, ["0x%X" % p for p in ps[:8]]))

# 找"成组出现"的指针块: 若多个串的指针都在同一 4 字节对齐窗口内
print("\n=== 指针簇 (同一 0x400 窗口内出现>=3个服务名指针) ===")
allpts = []
for n, ps in hits.items():
    for p in ps:
        allpts.append((p, n))
allpts.sort()
# 聚类
clusters = []
cur = []
for p, n in allpts:
    if cur and p - cur[-1][0] > 0x200:
        clusters.append(cur); cur = []
    cur.append((p, n))
if cur:
    clusters.append(cur)
for c in clusters:
    if len(c) >= 3:
        print("  cluster @0x%X .. 0x%X  (%d 项)" % (c[0][0], c[-1][0], len(c)))
        for p, n in c:
            print("      0x%06X -> %s" % (p, n))

# 转储最大簇的原始区段, 按 u32 逐项解析
if clusters:
    big = max(clusters, key=len)
    lo = big[0][0] - 0x20
    hi = big[-1][0] + 0x40
    print("\n=== 最大簇原始区段 0x%X-0x%X 按 u32 解析 ===" % (lo, hi))
    rev = {v: k for k, v in names.items()}
    p = lo
    while p + 4 <= hi:
        v = struct.unpack_from("<I", data, p)[0]
        tgt = None
        if BASE <= v < BASE + len(data):
            so = v - BASE
            if so in rev:
                tgt = rev[so]
            else:
                # 试读串
                e = data.find(b"\x00", so)
                if 0 < e - so < 48:
                    try:
                        s = data[so:e].decode("ascii")
                        if all(32 <= c < 127 for c in data[so:e]):
                            tgt = "str:" + s
                    except Exception:
                        pass
        print("  0x%06X: 0x%08X %s" % (p, v, tgt or ""))
        p += 4
