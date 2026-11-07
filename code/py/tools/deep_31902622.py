#!/usr/bin/env python3
"""31902622 深挖: 跨 run 是否恒定? 与 16 字节串/MAC 的关系? 是不是 hash/MAC 派生?"""
import json, collections, hashlib, zlib
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

V=31902622
print("V=31902622 = 0x%08X" % V)
print("bits:", bin(V))
print("hex bytes LE:", V.to_bytes(4,'little').hex())

# 收集所有 71/4 记录, 看 V 是否恒定 & 其它字段
vals=collections.Counter(); sess=collections.Counter(); mac=collections.Counter(); runs=collections.Counter()
for r in recs:
    if r.get("svc")==71 and r.get("task")==4:
        p=bytes.fromhex(r["payload"])
        # u32 at offset 0x2d (45)
        import struct
        v=struct.unpack_from("<I",p,45)[0]
        vals[v]+=1
        sess[p[6:22].decode('latin1')]+=1
        mac[p[0x3e:0x4f].decode('latin1')]+=1
        runs[r.get("run","?")]+=1
print("\n71/4 条数:", sum(vals.values()))
print("u32 值分布:", dict(vals))
print("会话串分布:", dict(sess))
print("MAC 分布:", dict(mac))
print("跨 run 数:", len(runs))

# 是否是 16字节串 的某种哈希的低32位?
s=b"nQloP0oCVWR6RDJS"
m=b"D4-93-90-18-55-10"
targets = {"sess":s, "mac":m, "sess+mac":s+m, "mac+sess":m+s,
           "sess+NUL":s+b"\0", "sess_upper":s.upper(), "sess_lower":s.lower()}
print("\n=== 尝试 hash 低32位 == V ? ===")
for name,data in targets.items():
    for algo in ["md5","sha1","sha256","sha512"]:
        h=hashlib.new(algo,data).digest()
        for endian in ("little","big"):
            lo=int.from_bytes(h[:4],endian)
            hi=int.from_bytes(h[-4:],endian)
            if lo==V: print("  HIT %s(%s) low4 %s"%(algo,name,endian))
            if hi==V: print("  HIT %s(%s) last4 %s"%(algo,name,endian))
    # crc32
    if (zlib.crc32(data)&0xffffffff)==V: print("  HIT crc32(%s)"%name)
print("done hash test")

# 31902622 是否是某常见常量? 与 build 1649370 关系?
print("\n=== 算术关系 ===")
print("1649370*? =", V/1649370 if 1649370 else 0)
print("V - 1649370 =", V-1649370)
print("V as unix ts:", __import__("datetime").datetime.utcfromtimestamp(V))
print("V/1000 ts:", __import__("datetime").datetime.utcfromtimestamp(V/1000))
