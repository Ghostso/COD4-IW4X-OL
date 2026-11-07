#!/usr/bin/env python3
"""提取每个房间消息类 vtable[0..2] 的函数地址。"""
import re
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    names = []
    for m in re.finditer(rb"\.\?A[VU]dwRoom[A-Za-z_]*@@", b):
        names.append((m.group().decode("latin1"),
                      BASE + m.start() - 8))

    print("%-50s %-10s %-10s %-10s %-10s" %
          ("class", "vtable", "[0]", "[1]", "[2]"))
    ok = 0
    for name, td in names:
        pat = struct.pack("<I", td)
        col = None
        k = 0
        while True:
            i = b.find(pat, k)
            if i < 0:
                break
            c = i - 12
            if c >= 0 and b[c:c + 12] == b"\0" * 12:
                col = BASE + c
                break
            k = i + 1
        if col is None:
            continue
        j = b.find(struct.pack("<I", col))
        if j < 0:
            continue
        vt = BASE + j
        o = vt - BASE
        f = [struct.unpack_from("<I", b, o + 4 * i)[0] for i in range(3)]
        print("%-50s %#-10x %#-10x %#-10x %#-10x" %
              (name.replace(".?AV", "").replace(".?AU", "")
               .replace("@@", ""), vt, f[0], f[1], f[2]))
        ok += 1
    print("\n%d 个" % ok)


if __name__ == "__main__":
    main()
