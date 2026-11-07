#!/usr/bin/env python3
"""用实测结构解析 dwRoomMessage* 的 RTTI：
   [vftable=0x00D77818][0][".?AV<Name>@@"]
   随后紧跟 [vftable][0][".?AV<Next>@@"]
COL = TypeDescriptor - 16（sig/off/cd/pTD 四字段，pTD 在 +12）
vtable = 指向 COL 的地址
"""
import re
import struct

EXE = r"工具\EX035_DIR\codoMP_client_shipRetail.exe"
IB = 0x8A8000


def main():
    b = open(EXE, "rb").read()
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    so = e + 24 + osz
    secs = []
    for i in range(nsec):
        o = so + i * 40
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        secs.append(("s%d" % i, IB + va, vs, rp, rs))

    def off2va(off):
        for nm, va, vs, rp, rs in secs:
            if rp <= off < rp + rs:
                return va + (off - rp)
        return None

    # 找所有 ".?A[VU]dwRoom" 名字，并取其前 9 字节处的 vftable 指针
    out = []
    for m in re.finditer(rb"\.\?A[VU]dwRoom[A-Za-z_]*@@", b):
        off = m.start()
        name = m.group().decode("latin1")
        td_start = off - 8          # [vftable 4][0 4][name]
        if td_start < 0:
            continue
        vft = struct.unpack_from("<I", b, td_start)[0]
        td_va = off2va(td_start)
        out.append((name, td_va, vft))

    print("名字 %d 个；前 16 个的 TypeDescriptor VA 与 vftable：" % len(out))
    for name, td, vft in out[:16]:
        print("  %-56s TD=%s vft=%#x" % (
            name, ("%#x" % td) if td else "?", vft))

    # 校验：vftable 应统一为 0x00D77818
    s = {v for _, _, v in out}
    print("\nvftable 取值集合：%s" % {hex(x) for x in s})

    # 找 COL：搜索 td_va 作为 pTD 字段（COL 起点 = 该处 - 12）
    print("\n尝试解析 COL → vtable：")
    hits = 0
    for name, td, _vft in out[:8]:
        if not td:
            continue
        pat = struct.pack("<I", td)
        k = 0
        while True:
            i = b.find(pat, k)
            if i < 0:
                break
            col_va = off2va(i - 12)
            if col_va:
                # 找指向 col 的 vtable
                p2 = struct.pack("<I", col_va)
                j = b.find(p2)
                if j >= 0:
                    print("  %-52s COL=%#x vtable=%#x" % (
                        name, col_va, off2va(j) or 0))
                    hits += 1
                    break
            k = i + 1
    print("命中 %d" % hits)


if __name__ == "__main__":
    main()
