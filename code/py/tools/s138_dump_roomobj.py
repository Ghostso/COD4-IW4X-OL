#!/usr/bin/env python3
"""138: 房间运行期对象 vs 静态地址 —— 找出**动态分配的房间对象**并读其关键字段。

已知静态: 房间对象全局槽 0x082E13FC(非0=有对象), 链路 [0x8269774]->+0x4F4=sub
目标: 从 dump 里解析 0x82E13FC 指向的 dwRoomImp 对象, 读 vtable 确认类,
      并尝试读它的事件计数器/状态字段(判断"收到过多少事件")。
用法: python -X utf8 tools\s138_dump_roomobj.py <dumpdir>
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VA0 = 0x400000
dump = sys.argv[1]

regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))
regs.sort()


def rd(va, n=4):
    for base, size, fn in regs:
        if base <= va < base + size:
            try:
                with open(os.path.join(dump, "mem", fn), "rb") as f:
                    f.seek(va - base)
                    return f.read(min(n, base + size - va))
            except OSError:
                return None
    return None


def u32(va):
    d = rd(va, 4)
    return struct.unpack("<I", d)[0] if d and len(d) == 4 else None


print("=== 链路解析 ===")
for name, va in (("roomObjSlot", 0x082E13FC), ("connSlot", 0x08269774),
                 ("appMode", 0x00E59D20), ("roomGate", 0x0849BA30),
                 ("stateMachine", 0x0849BA34), ("loginStage", 0x084ABA50)):
    print("  %-14s @%08X = %s" % (name, va, hex(u32(va)) if u32(va) is not None else "无"))

room = u32(0x082E13FC)
if room:
    print("\n=== dwRoomImp 对象 @%08X ===" % room)
    vt = u32(room)
    print("  [0x00] vtable = %s" % (hex(vt) if vt else "无"))
    # 读前 0x200 字节的 dword, 标出"像指针"的
    blob = rd(room, 0x200)
    if blob:
        for off in range(0, min(len(blob), 0x100), 4):
            v = struct.unpack_from("<I", blob, off)[0]
            tag = ""
            if VA0 <= v < 0x02000000:
                tag = " <- 像镜像内地址"
            elif 0x03000000 <= v < 0x10000000:
                tag = " <- 像堆地址"
            elif v != 0:
                tag = "  值=%d" % v
            if off < 0x60 or tag:
                print("    +0x%03X = %08X%s" % (off, v, tag))

conn = u32(0x08269774)
if conn:
    sub = u32(conn + 0x4F4)
    print("\n=== 连接链 @%08X -> sub @%s ===" % (conn, hex(sub) if sub else "无"))
    if sub:
        for off in (0x5E8, 0x5FC, 0x604, 0x608, 0x60C):
            print("    sub+0x%03X = %s" % (off, hex(u32(sub + off))))
