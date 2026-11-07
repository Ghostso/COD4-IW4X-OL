#!/usr/bin/env python3
"""本地逆向佐证 0x66=Messaging2:
(1) 判 E 镜像是否 PE (节表);
(2) 大小写不敏感搜 Messaging* 全部命中及上下文;
(3) 搜 lowercase 服务注册名候选。
"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)

# --- (1) PE 头 ---
print("=== PE 检查 ===")
if data[:2] == b"MZ":
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    print("MZ, e_lfanew=0x%X" % e_lfanew)
    if data[e_lfanew:e_lfanew+4] == b"PE\0\0":
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", data, coff+2)[0]
        optsz = struct.unpack_from("<H", data, coff+16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        imagebase = struct.unpack_from("<Q", data, opt+24)[0] if magic==0x20b else struct.unpack_from("<I", data, opt+28)[0]
        print("PE32%s  nsec=%d  imagebase=0x%X" % ("+" if magic==0x20b else "", nsec, imagebase))
        sec = opt + optsz
        print("节表:")
        for i in range(nsec):
            off = sec + i*40
            name = data[off:off+8].rstrip(b"\0").decode("latin1")
            vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", data, off+8)
            print("  %-8s VA=0x%08X VS=0x%08X RAW=0x%08X RS=0x%08X" % (name, vaddr, vsize, raddr, rsize))
    else:
        print("无 PE 签名")
else:
    print("非 MZ 头: %r" % data[:16])

# --- (2) Messaging 全谱 ---
print("\n=== 大小写不敏感 'messaging' 命中 ===")
low = data.lower()
needle = b"messaging"
i = 0; hits = []
while True:
    p = low.find(needle, i)
    if p < 0: break
    hits.append(p); i = p+1
    if len(hits) > 60: break
print("总命中(截断60):", len(hits))
for p in hits:
    # 取该处前后可打印串
    lo = p
    while lo > 0 and 32 <= data[lo-1] < 127: lo -= 1
    hi = p
    while hi < N and 32 <= data[hi] < 127: hi += 1
    s = data[lo:hi].decode("latin1")
    print("  0x%08X  %r" % (p, s[:100]))
