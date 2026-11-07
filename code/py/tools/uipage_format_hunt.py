#!/usr/bin/env python3
"""在镜像里找 UIPage / UIClick 的格式串来源.
思路1: 打印所有含 'UIPage' 的 NUL 串 + 前后邻串.
思路2: 找引用 UIPage(0x9C7090) 地址的指令/指针(4字节 LE, VA 0x9C7090+0x400000).
思路3: 找镜像里任何形如 'xxx|${TIMESTAMP_OFFSET' 的串 (遥测宏入口 -> 可能别处有 UIPage 模板).
思路4: 找任何以 'UIPage|' 开头的串(不管后面是什么).
"""
import struct, re
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

def cstr(off, maxlen=400):
    e = d.find(b"\x00", off)
    if e < 0: e = off + maxlen
    return d[off:min(e, off + maxlen)]

print("=== 1) UIPage / UIClick 串位置 ===")
for name in (b"UIPage", b"UIClick"):
    for m in re.finditer(re.escape(name), d):
        off = m.start()
        # 只认"串开头"(前一字节 NUL 或非可打印)
        if off and 32 <= d[off-1] < 127:
            continue
        s = cstr(off)
        print("  0x%X  len=%3d  %r" % (off, len(s), s[:120]))
        # 邻串
        back = d.rfind(b"\x00", 0, off - 1)
        if back >= 0 and off - back < 400:
            print("        prev: %r" % cstr(back + 1)[:100])
        print("        next: %r" % cstr(off + len(s) + 1)[:100])

print()
print("=== 2) 任何以 'UIPage|' 开头的串 ===")
for m in re.finditer(rb"UIPage\|", d):
    off = m.start()
    if off and 32 <= d[off-1] < 127:
        continue
    print("  0x%X  %r" % (off, cstr(off)[:200]))

print()
print("=== 3) 指针引用(4B LE = 0x9C7090+0x400000) ===")
for name, fo in ((b"UIPage", 0x9C7090), (b"UIClick", 0x9C7088)):
    ptr = fo + VA
    hits = [m.start() for m in re.finditer(re.escape(struct.pack("<I", ptr)), d)]
    print("  %s str@file 0x%X  ptr=0x%X  引用 %d 处: %s" %
          (name.decode(), fo, ptr, len(hits), [hex(h) for h in hits[:20]]))

print()
print("=== 4) 含 ${TIMESTAMP_OFFSET 的串(前 60) ===")
c = 0
for m in re.finditer(rb"\$\{TIMESTAMP_OFFSET", d):
    off = m.start()
    st = d.rfind(b"\x00", max(0, off - 120), off)
    s = d[st + 1:off + 60]
    if 32 <= d[off-1]:
        print("  0x%X  ...%r" % (off, s[:80]))
        c += 1
        if c >= 60:
            break
