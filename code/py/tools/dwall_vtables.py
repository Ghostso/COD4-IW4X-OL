#!/usr/bin/env python3
"""枚举 dwRoom 位流类的**全部** vtable（含 dwroom_serializers 漏掉的），
并从 RTTI 名反查类名。用于补齐类型号表缺口 11 / 19 / 25。"""
import re
import struct

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
LO, HI = 0xdc74e0, 0xdc7c40


def main():
    b = open(DUMP, "rb").read()
    # 1) RTTI: name -> TD -> COL
    rtti = {}
    for m in re.finditer(rb"\.\?A[VU]dwRoom[A-Za-z_0-9]*@@", b):
        nm = m.group().decode("latin1")
        short = re.sub(r"^\.\?A[VU]", "", nm).rstrip("@")
        td = BASE + m.start() - 8
        pat = struct.pack("<I", td)
        k = 0
        while True:
            i = b.find(pat, k)
            if i < 0:
                break
            c = i - 12
            if c >= 0 and b[c:c + 12] == b"\0" * 12:
                rtti[short] = BASE + c
                break
            k = i + 1
    col2name = {v: k for k, v in rtti.items()}

    # 2) 枚举 vtable 区
    rows = []
    for va in range(LO, HI, 4):
        v = struct.unpack_from("<I", b, va - BASE)[0]
        if not (0xdf0000 <= v < 0xe20000):
            continue
        # vtable[0]=COL, vtable[1],[2]=dtor/serialize
        s = struct.unpack_from("<IIII", b, va - BASE)
        name = col2name.get(s[0], "?")
        rows.append((va, s[0], name, s[1], s[2]))
    print("=== %#x..%#x 区间的 vtable 共 %d 个 ===" % (LO, HI, len(rows)))
    print("%-12s %-12s %-46s %-12s %-12s" % (
        "vtable", "COL", "class", "slot1", "slot2"))
    for va, col, name, s1, s2 in rows:
        print("%#010x %#010x %-46s %#010x %#010x" % (va, col, name, s1, s2))
    # 未命名
    un = [r for r in rows if r[2] == "?"]
    print("\n未命名的 vtable: %d" % len(un))
    for va, col, _, s1, s2 in un:
        print("  %#010x COL=%#010x slots=%#x/%#x" % (va, col, s1, s2))


if __name__ == "__main__":
    main()
