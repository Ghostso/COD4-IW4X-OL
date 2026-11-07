#!/usr/bin/env python3
"""138: 找 [reg+0x25B8] 的读取点（= 谁调用房间消息接收回调）。
模式: call dword [reg+0x25B8]  => FF 90 B8 25 00 00
       mov reg,[reg+0x25B8]    => 8B 8? B8 25 00 00
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

PATS = [
    ("call [reg+0x25B8]", re.compile(rb"\xff[\x90\x91\x92\x93\x94\x95\x96\x97]\xb8\x25\x00\x00")),
    ("mov r32,[reg+0x25B8]", re.compile(rb"\x8b[\x80-\xbf]\xb8\x25\x00\x00")),
    ("mov [reg+0x25B8],r32", re.compile(rb"\x89[\x80-\xbf]\xb8\x25\x00\x00")),
    ("push [reg+0x25B8]", re.compile(rb"\xff[\xb0-\xb7]\xb8\x25\x00\x00")),
]

for name, pat in PATS:
    print("=" * 70)
    print(name)
    n = 0
    for m in pat.finditer(d):
        n += 1
        print("   0x%08X  %s" % (VA + m.start(), d[m.start():m.start() + 10].hex()))
    print("   共 %d 处" % n)

# 顺带：0x25C8 会话对象的写入点
print("=" * 70)
print("mov [reg+0x25C8],r32  （谁把会话对象存进去）")
pat = re.compile(rb"\x89[\x80-\xbf]\xc8\x25\x00\x00")
n = 0
for m in pat.finditer(d):
    n += 1
    print("   0x%08X  %s" % (VA + m.start(), d[m.start():m.start() + 10].hex()))
print("   共 %d 处" % n)
