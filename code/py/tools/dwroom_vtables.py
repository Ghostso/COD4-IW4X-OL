#!/usr/bin/env python3
"""把 dwRoomMessage* 类与其 vtable / serialize 函数对应起来。
每个类的 RTTI CompleteObjectLocator 指向 vtable，vtable 里是虚函数。"""
import re
import struct

EXE = r"工具\EX035_DIR\codoMP_client_shipRetail.exe"


def main():
    b = open(EXE, "rb").read()
    IB = 0x8A8000

    # 节表
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    so = e + 24 + osz
    secs = []
    for i in range(nsec):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        secs.append((nm, IB + va, vs, rp, rs))

    def off2va(off):
        for nm, va, vs, rp, rs in secs:
            if rp <= off < rp + rs:
                return va + (off - rp)
        return None

    def va2off(va):
        for nm, sva, vs, rp, rs in secs:
            if sva <= va < sva + max(vs, rs):
                d = va - sva
                return rp + d if d < rs else None
        return None

    # 找所有 dwRoomMessage* 名字，再找指向它的 TypeDescriptor
    names = []
    for m in re.finditer(rb"\.\?A[VU]dwRoomMessage[A-Za-z_]*@@", b):
        names.append((m.start(), m.group().decode("latin1")))

    print("共 %d 个 dwRoomMessage* 名" % len(names))

    # 反向：对每个名字，在 .data/.rdata 里找"name_va - 9" 作为 TypeDescriptor
    results = []
    for off, nm in names:
        name_va = off2va(off)
        if not name_va:
            continue
        td_va = name_va - 9          # TypeDescriptor = name - 9
        pat = struct.pack("<I", td_va)
        # 找引用该 TypeDescriptor 的 CompleteObjectLocator
        found = []
        k = 0
        while True:
            i = b.find(pat, k)
            if i < 0 or len(found) > 2:
                break
            # COL 结构: sig(4) off(4) cd(4) pTD(4) pCD(4)
            # 若 i 是 pTD 字段，则 COL 起点 = i-12
            col_va = off2va(i - 12)
            if col_va:
                found.append(col_va)
            k = i + 1
        for col in found:
            # 找引用 COL 的 vtable（第一个 dword 是 COL 指针）
            p2 = struct.pack("<I", col)
            j = 0
            while True:
                k2 = b.find(p2, j)
                if k2 < 0:
                    break
                vt_va = off2va(k2)
                if vt_va:
                    results.append((nm, vt_va, col))
                    break
                j = k2 + 1

    print("解析出 vtable 的类：%d" % len(results))
    for nm, vt, col in results[:60]:
        print("  %-56s vtable=%#010x" % (nm, vt))


if __name__ == "__main__":
    main()
