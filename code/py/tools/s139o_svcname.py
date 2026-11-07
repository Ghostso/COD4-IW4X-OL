# -*- coding: utf-8 -*-
"""139o: 定位 "room"/"team"/"vote"/"task" 字符串地址，并找 push 它的调用点。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000
N = len(d)

def find_str(s):
    b = s.encode() + b"\0"
    out, i = [], 0
    while True:
        j = d.find(b, i)
        if j < 0:
            break
        out.append(j + VA)
        i = j + 1
    return out

def push_refs(va):
    p = struct.pack("<I", va)
    out, i = [], 0
    while True:
        j = d.find(p, i)
        if j < 0:
            break
        # 检查前 1 字节是否 0x68 (push imm32)
        if j - 1 >= 0 and d[j - 1] == 0x68:
            out.append((j - 1) + VA)
        i = j + 1
    return out

for name in ("room", "team", "vote", "task", "zone", "page", "list", "slot", "main", "menu"):
    for va in find_str(name):
        pr = push_refs(va)
        if pr:
            print(f"<{name}> @0x{va:08X}  push 调用点: {[hex(x) for x in pr]}")
