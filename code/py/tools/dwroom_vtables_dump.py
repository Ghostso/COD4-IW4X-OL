#!/usr/bin/env python3
"""从运行时镜像解析 dwRoomMessage* 的 COL → vtable。"""
import re
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    names = []
    for m in re.finditer(rb"\.\?A[VU]dwRoom[A-Za-z_]*@@", b):
        off = m.start()
        td_off = off - 8
        if td_off < 0:
            continue
        td_va = BASE + td_off
        names.append((m.group().decode("latin1"), td_va))
    print("镜像内 dwRoom RTTI 名 %d 个" % len(names))

    print("\n%-56s %-10s %-10s %s" % ("class", "TD", "COL", "vtable"))
    ok = 0
    for name, td in names:
        pat = struct.pack("<I", td)
        col = vt = None
        k = 0
        while True:
            i = b.find(pat, k)
            if i < 0:
                break
            # COL 布局: sig(4) off(4) cd(4) pTD(4) pCD(4)
            # 若 i 指向 pTD，则 COL 起点 = i-12，且前 3 个 dword 应为 0/0/0
            c = i - 12
            if c >= 0 and b[c:c + 12] == b"\0" * 12:
                col = BASE + c
                break
            k = i + 1
        if col is not None:
            p2 = struct.pack("<I", col)
            j = b.find(p2)
            if j >= 0:
                vt = BASE + j
        if vt:
            ok += 1
            print("%-56s %#-10x %#-10x %#x" % (name, td, col, vt))
    print("\n解析成功 %d / %d" % (ok, len(names)))


if __name__ == "__main__":
    main()
