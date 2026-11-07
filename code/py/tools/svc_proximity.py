#!/usr/bin/env python3
"""在 E 镜像里找: 服务名串(leaderboard/matchmaking/...)附近 ±0x400 是否出现 u32/u16 值 102 或已知服务号。
也找连续 u32 表中同时含 21 与 80/93 的位置。"""
import struct

PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()
N = len(data)

names = [b"leaderboard", b"Leaderboard", b"matchmaking", b"marketplace",
         b"publisher_storage", b"PublisherStorage", b"publisherStorage"]

def findall(b):
    out=[]; i=0
    while True:
        p=data.find(b,i)
        if p<0: return out
        out.append(p); i=p+1

print("=== 服务名串附近的 u32 值 ===")
for nm in names:
    for p in findall(nm)[:8]:
        # 读前后 u32
        vals=[]
        for k in range(-0x40, 0x41, 4):
            q=p+k
            if 0<=q<N-4:
                vals.append(struct.unpack_from("<I",data,q)[0])
        interesting=[v for v in vals if v in (102,21,80,93,6,28,4,9,11,71,68,8,10,3,29)]
        print("  %-20s @0x%X  附近含服务号: %s" % (nm.decode(), p, interesting))

print("\n=== 找含 21 且 ±0x80 内有 80 或 93 或 102 的 u32 位置 ===")
cnt=0
for p in range(0, N-4, 4):
    v=struct.unpack_from("<I",data,p)[0]
    if v==21:
        near=set()
        for k in range(-0x80,0x81,4):
            q=p+k
            if 0<=q<N-4:
                near.add(struct.unpack_from("<I",data,q)[0])
        if 80 in near or 93 in near or 102 in near:
            print("  @0x%X  21 附近: %s" % (p, sorted(x for x in near if x in (80,93,102,21))))
            cnt+=1
            if cnt>40: break
print("  共",cnt)
