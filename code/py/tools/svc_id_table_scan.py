#!/usr/bin/env python3
"""找 E 镜像里同时含多个已知服务号 {6,8,10,11,21,28,68,71,80,93,102} 的密集 u32 区。
若存在, 即静态 service-id 表, 可看 102 邻位是不是 messaging 相关。"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data); BASE = 0x400000
KNOWN = {6,8,10,11,21,28,68,71,80,93,102}

# 滑窗: 每 256 字节统计命中数
best = []
step = 256
for off in range(0, N-step, step):
    win = data[off:off+step]
    vals = set()
    for k in range(0, step-4, 4):
        v = struct.unpack_from("<I", win, k)[0]
        if v in KNOWN:
            vals.add(v)
    if len(vals) >= 4:
        best.append((off, len(vals), sorted(vals)))

best.sort(key=lambda x: -x[1])
print("=== 命中>=4 个已知服务号的 256B 窗口 (前25) ===")
for off, cnt, vals in best[:25]:
    print("  file0x%08X VA0x%08X  hit=%d  %s" % (off, off+BASE, cnt, vals))
print("\n总窗口数:", len(best))

# 对最密集的几个, dump 出 u32 序列
if best:
    for off, cnt, vals in best[:3]:
        print("\n=== dump file0x%08X (hit=%d) ===" % (off, cnt))
        seq = []
        for k in range(0, 256, 4):
            seq.append(struct.unpack_from("<I", data, off+k)[0])
        print("  u32:", seq)
