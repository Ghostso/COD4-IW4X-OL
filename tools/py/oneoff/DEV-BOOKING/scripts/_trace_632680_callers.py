# -*- coding: utf-8 -*-
"""P0 收尾: 穷举 0x632680 的所有可能调用路径。

手段:
 A. call rel32 / dword 引用 全覆盖
 B. 两个 vtable 起点是否被引用（= 是否被注册/实例化）
 C. 同表其它槽是否被引用（判断整表是否被注册）
"""
import struct

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
img = open(IMG, "rb").read()
TARGET = 0x632680
VTABLE1 = 0xDC7270


def call_rel32_hits(target):
    out = []
    for i in range(0, len(img) - 5):
        if img[i] == 0xE8:
            rel = struct.unpack_from("<i", img, i + 1)[0]
            if 0x400000 + i + 5 + rel == target:
                out.append(0x400000 + i)
    return out


def dword_refs(value):
    pat = struct.pack("<I", value)
    out = []
    s = 0
    while True:
        i = img.find(pat, s)
        if i < 0:
            return out
        out.append(0x400000 + i)
        s = i + 1


def main():
    print("=" * 78)
    print("A. 直接到达 0x%08X 的路径" % TARGET)
    print("=" * 78)
    print("  call rel32 :", [hex(h) for h in call_rel32_hits(TARGET)] or "无")
    print("  dword 引用 :", [hex(h) for h in dword_refs(TARGET)] or "无")
    print()
    print("=" * 78)
    print("B. vtable 起点 0x%08X 是否被引用" % VTABLE1)
    print("=" * 78)
    rs = dword_refs(VTABLE1)
    print("  被引用 %d 处: %s" % (len(rs), [hex(x) for x in rs[:10]]))
    print()
    print("=" * 78)
    print("C. 同表关键槽是否被引用")
    print("=" * 78)
    for slot in (0x13C, 0x140, 0x144, 0x148, 0x14C):
        v = struct.unpack_from("<I", img, VTABLE1 + slot - 0x400000)[0]
        rs2 = dword_refs(v) if 0x401000 <= v < 0xE65000 else []
        print("  +0x%03X -> 0x%08X  引用 %d 处 %s"
              % (slot, v, len(rs2), [hex(x) for x in rs2[:4]]))


if __name__ == "__main__":
    main()
