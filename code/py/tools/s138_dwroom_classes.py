#!/usr/bin/env python3
"""138: 房间事件的**客户端分发点** —— dwRoomMatch / MyEventHandler / dwRoomMatchUber
① 列出所有 dw* / My* 类名
② 用 vtname 解析关键 vtable，确认类身份
③ 找 MyEventHandler@?5??Init@dwRoomMatch 的登记函数
"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def rd(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f < N - 4 else None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def short(nm):
    s = nm
    for sep in ("AV", "AU"):
        if sep in s:
            s = s.split(sep, 1)[1]
            break
    return s.split("@@")[0]


names = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]{2,120}@@", d):
    names[VA + m.start()] = m.group().decode("latin1")

print("=== 所有 dw* 类 (去重) ===")
dws = sorted({short(n) for n in names.values() if short(n).startswith("dw")})
for s in dws:
    print("   ", s)

print("\n=== 所有 My* 类 ===")
for s in sorted({short(n) for n in names.values() if short(n).startswith("My")}):
    print("   ", s)

print("\n=== 所有 Handler/Event 相关类 ===")
for s in sorted({short(n) for n in names.values()
                 if "andler" in short(n) or "Event" in short(n)}):
    print("   ", s)

# 解析 dwRoomMessageReady 的 vtable：先找它的 type_info host, 再找谁引用
print("\n=== 定位 dwRoomMessageReady 的 vtable ===")
target_hosts = []
for va, nm in names.items():
    if "dwRoomMessageReady@@" in nm or "dwRoomMatchUber@@" in nm:
        host = va - 8
        target_hosts.append((short(nm), host))
        print("   %-30s name=0x%08X host=0x%08X" % (short(nm), va, host))

for sname, host in target_hosts:
    pat = struct.pack("<I", host)
    pos = 0
    found = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        found += 1
        if found <= 5:
            print("   [%s] host 引用 @0x%08X" % (sname, VA + i))
    print("   [%s] host 引用共 %d 处" % (sname, found))
