#!/usr/bin/env python3
"""DEDRUN_RUNTIME_0x810000.bin 的内存布局探针。

文件名为 0x810000 —— 需实测确认它是不是 "从 0x810000 起的镜像"。
做法: 在文件里找已知 PE 头/MZ 或已知节内容, 反推基址。
"""
import sys

b = open(sys.argv[1], "rb").read()
print("size=%#x (%d MB)" % (len(b), len(b) // (1024 * 1024)))
print("first16:", b[:16].hex())
print("first64:", b[:64])

# 找 MZ 头
import re
hits = [m.start() for m in re.finditer(b"MZ\x90\x00\x03", b)]
print("MZ90 hits:", len(hits), [hex(h) for h in hits[:10]])

# 找 "This program cannot be run in DOS mode"
m = b.find(b"This program cannot be run in DOS mode")
print("DOS stub at:", hex(m) if m >= 0 else None)

# 找典型 PE 特征: 'PE\0\0' 在 MZ+0x80 附近
for h in hits[:5]:
    if h + 0x100 < len(b):
        import struct
        e = struct.unpack_from("<I", b, h + 0x3C)[0]
        print("  MZ@%#x e_lfanew=%#x -> %s" % (h, e, b[h + e:h + e + 4] if h + e + 4 < len(b) else "?"))

# 找已知的 Base.dll 特征串
for s in (b"codoMP_client_shipRetailBase.dll", b"dwRoomMessageStartGame", b"ClientLogin|%s"):
    i = b.find(s)
    print("%-40s %s" % (s.decode("latin1", "replace"), hex(i) if i >= 0 else "NOT FOUND"))
