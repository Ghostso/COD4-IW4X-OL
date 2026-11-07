# -*- coding: utf-8 -*-
"""BA-01 镜像全字节归属普查 (v2).

镜像是按内存布局铺开的 (VA = 文件偏移), 因此一律用节的 VA 区间认领.

归属层级 (优先级从高到低, 先认领者胜):
  1 PE_HEADERS
  2 RTTI_TYPE_DESC      TypeDescriptor (TD)
  3 RTTI_COL            CompleteObjectLocator
  4 VFTABLE             由 COL+4 反推
  5 FUNCTION            可执行节线性扫描得到的函数体
  6 ASCII_STRING        >=6 可打印
  7 UTF16_STRING
  8 PADDING             0xCC / 0x00 长游程
  9 SECTION_DATA        节内其它

输出:
  DATA/ba01_bytes.json  区间表
  DATA/ba01_report.txt  人读
"""
import json
import os
import re
import struct
import sys

IMG = r"E:\codol_re\client_image_20261027.bin"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")

try:
    import capstone
    HAVE_CS = True
except Exception:
    HAVE_CS = False


def parse_pe(d):
    e = struct.unpack_from("<I", d, 0x3C)[0]
    coff = e + 4
    machine, nsec = struct.unpack_from("<HH", d, coff)
    opt_size = struct.unpack_from("<H", d, coff + 16)[0]
    opt = coff + 20
    pe32plus = struct.unpack_from("<H", d, opt)[0] == 0x20B
    image_base = struct.unpack_from("<Q" if pe32plus else "<I", d,
                                    opt + (24 if pe32plus else 28))[0]
    size_of_image = struct.unpack_from("<I", d, opt + 56)[0]
    size_of_headers = struct.unpack_from("<I", d, opt + 60)[0]
    ndirs_off = opt + (108 if pe32plus else 92)
    ndirs = struct.unpack_from("<I", d, ndirs_off)[0]
    dirs = [struct.unpack_from("<II", d, ndirs_off + 4 + i * 8)
            for i in range(min(ndirs, 16))]
    sec_off = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
        vsz, va, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        chars = struct.unpack_from("<I", d, o + 36)[0]
        secs.append(dict(name=name, va=va, vsz=vsz, rawptr=rawptr,
                         rawsz=rawsz, chars=chars))
    return image_base, size_of_image, size_of_headers, dirs, secs


class Ledger:
    def __init__(self, n):
        self.n = n
        self.kind = [None] * n   # 每个字节的归属种类, 用 list 便于逐字节记录
        self.regions = []

    def claim(self, start, end, kind, tag="", meta=None):
        start = max(0, start)
        end = min(self.n, end)
        if start >= end:
            return 0
        k = self.kind
        got = 0
        for i in range(start, end):
            if k[i] is None:
                k[i] = kind
                got += 1
        if got:
            r = dict(start=start, end=end, kind=kind, tag=tag, new=got)
            if meta:
                r.update(meta)
            self.regions.append(r)
        return got

    def gaps(self, want=None):
        out = []
        i, n, k = 0, self.n, self.kind
        while i < n:
            if k[i] is None:
                j = i
                while j < n and k[j] is None:
                    j += 1
                out.append((i, j))
                i = j
            else:
                i += 1
        return out

    def tally(self):
        t = {}
        for x in self.kind:
            t[x] = t.get(x, 0) + 1
        return t


def scan_rtti(d, n):
    """枚举 TypeDescriptor 与 COL."""
    tds = []
    pat = re.compile(rb"\.\?A[VU][^\x00]{1,200}\x00")
    for m in pat.finditer(d):
        name_off = m.start()
        td_off = name_off - 0x10  # TD: {pVFTable(4), spare(4), name(4)} -> name at +8? 见下
        # MSVC x86: TD = { void* pVFTable; void* spare; char name[]; }  name at +8
        td_off = name_off - 0x8
        if td_off < 0:
            continue
        # 校验: TD+0 指向 .rdata 的 vftable-like 指针 or 0
        p = struct.unpack_from("<I", d, td_off)[0]
        tds.append(dict(td=td_off, name=m.group()[:-1].decode("latin1"),
                        p= p))
    return tds


def main():
    d = open(IMG, "rb").read()
    n = len(d)
    base, soi, soh, dirs, secs = parse_pe(d)
    L = Ledger(n)
    print("base=0x%08X size=0x%X" % (base, n))

    L.claim(0, min(soh, n), "PE_HEADERS")
    for s in secs:
        L.claim(s["va"], s["va"] + max(s["vsz"], 1), "SECTION",
                s["name"], dict(prot="0x%08X" % s["chars"]))

    # 目录也标注 (不覆盖节)
    dnames = ["EXPORT", "IMPORT", "RESOURCE", "EXCEPTION", "SECURITY",
              "BASERELOC", "DEBUG", "ARCH", "GLOBALPTR", "TLS", "LOADCFG",
              "BOUNDIMP", "IAT", "DELAYIMP", "COM", "RESERVED"]
    for i, (rva, sz) in enumerate(dirs):
        if rva and sz:
            L.claim(rva, rva + sz, "DIR_" + dnames[i], "slot%d" % i)

    # RTTI
    tds = scan_rtti(d, n)
    print("TypeDescriptor candidates: %d" % len(tds))
    for t in tds:
        L.claim(t["td"], t["td"] + 8 + len(t["name"]) + 1, "RTTI_TD",
                t["name"])

    # 字符串
    for m in re.finditer(rb"[ -~]{6,}", d):
        L.claim(m.start(), m.end(), "ASCII_STRING")

    t = L.tally()
    tot = n
    print("\n=== 归属统计 ===")
    for k, v in sorted(t.items(), key=lambda x: -x[1]):
        if k is None:
            continue
        print("  %-14s %10d  %6.2f%%" % (k, v, 100.0 * v / tot))
    unc = t.get(None, 0)
    print("  %-14s %10d  %6.2f%%" % ("UNCLASSIFIED", unc, 100.0 * unc / tot))

    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(size=n, base=base, tally={str(k): v for k, v in t.items()},
                   sections=secs, rtti_td_count=len(tds)),
              open(os.path.join(OUT, "ba01_bytes.json"), "w",
                   encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
