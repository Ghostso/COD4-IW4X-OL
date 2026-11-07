# -*- coding: utf-8 -*-
"""找出 0xDC7398/0xDC7838 所在 vtable 的真正起点，以及它被谁引用。"""
import struct

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
img = open(IMG, "rb").read()


def dword(va):
    return struct.unpack_from("<I", img, va - 0x400000)[0]


def is_code(v):
    return 0x401000 <= v < 0xE65000


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


for anchor in (0xDC73B0, 0xDC7850):
    print("=" * 78)
    print("anchor = 0x%08X  (accepted handler slot)" % anchor)
    print("=" * 78)
    cur = anchor
    while True:
        nxt = cur - 4
        v = dword(nxt)
        if is_code(v) or v == 0:
            cur = nxt
        else:
            break
    print("  table start candidate = 0x%08X  (%d slots)"
          % (cur, (anchor - cur) // 4 + 1))
    print("  DWORDs before table start:")
    for k in range(-6, 2):
        va = cur + k * 4
        print("     0x%08X  0x%08X" % (va, dword(va)))
    print()
    for d in (0, 4, 8, 12, -4):
        rs = dword_refs(cur + d)
        if rs:
            print("  refs to table_start%+d : %d  %s"
                  % (d, len(rs), [hex(x) for x in rs[:10]]))
    print()
