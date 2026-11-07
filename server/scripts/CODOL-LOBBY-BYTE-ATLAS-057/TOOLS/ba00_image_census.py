# -*- coding: utf-8 -*-
"""BA-00 镜像字节普查器.

目标: 把 client_image_20261027.bin 切成互不重叠的区间, 并逐字节计量归属.
任何没有被任何规则认领的字节, 都计入 UNCLASSIFIED 并以区间形式列出.

用法:
    python -I -B TOOLS\ba00_image_census.py
输出:
    DATA\ba00_census.json   区间表 (machine readable)
    DATA\ba00_census.txt    人读报告
"""
import bisect
import json
import os
import struct
import sys

IMG = r"E:\codol_re\client_image_20261027.bin"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")
BASE_DEFAULT = 0x400000  # VA = file_off + BASE


def parse_pe(d):
    """解析 PE, 返回 imagebase / sections."""
    if d[:2] != b"MZ":
        raise SystemExit("not MZ")
    e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
    if d[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise SystemExit("not PE")
    coff = e_lfanew + 4
    machine, nsec = struct.unpack_from("<HH", d, coff)
    opt_size = struct.unpack_from("<H", d, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", d, opt)[0]
    pe32plus = magic == 0x20B
    image_base = struct.unpack_from("<Q" if pe32plus else "<I",
                                   d, opt + (24 if pe32plus else 28))[0]
    size_of_image = struct.unpack_from("<I", d, opt + 56)[0]
    size_of_headers = struct.unpack_from("<I", d, opt + 60)[0]
    ndirs_off = opt + (108 if pe32plus else 92)
    ndirs = struct.unpack_from("<I", d, ndirs_off)[0]
    dirs = []
    for i in range(min(ndirs, 16)):
        rva, sz = struct.unpack_from("<II", d, ndirs_off + 4 + i * 8)
        dirs.append((rva, sz))
    sec_off = opt + opt_size
    sections = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
        vsz, va, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        chars = struct.unpack_from("<I", d, o + 36)[0]
        sections.append(dict(name=name, va=va, vsz=vsz, rawptr=rawptr,
                             rawsz=rawsz, chars=chars))
    return dict(image_base=image_base, size_of_image=size_of_image,
                size_of_headers=size_of_headers, dirs=dirs,
                sections=sections, pe32plus=pe32plus)


class Claimer:
    """按优先级把字节归属到区间; 后写的不覆盖先写的."""

    def __init__(self, n):
        self.n = n
        self.owner = bytearray(n)   # 0 = 未归类
        self.regions = []

    def claim(self, start, end, kind, tag=""):
        if end > self.n:
            end = self.n
        if start >= end or start < 0:
            return 0
        owner = self.owner
        got = 0
        for i in range(start, end):
            if owner[i] == 0:
                owner[i] = 1
                got += 1
        if got:
            self.regions.append(dict(start=start, end=end, kind=kind,
                                     tag=tag, new_bytes=got))
        return got

    def gaps(self):
        out = []
        i = 0
        n = self.n
        own = self.owner
        while i < n:
            if own[i] == 0:
                j = i
                while j < n and own[j] == 0:
                    j += 1
                out.append((i, j))
                i = j
            else:
                i += 1
        return out


def main():
    d = open(IMG, "rb").read()
    n = len(d)
    pe = parse_pe(d)
    base = pe["image_base"]
    print("image_base=0x%08X size=%d(0x%X) image_size_field=0x%X"
          % (base, n, n, pe["size_of_image"]))
    print("sections:")
    for s in pe["sections"]:
        print("  %-10s va=0x%08X vsz=0x%08X raw=0x%08X@0x%08X prot=0x%08X"
              % (s["name"], s["va"], s["vsz"], s["rawsz"], s["rawptr"],
                 s["chars"]))

    c = Claimer(n)

    # --- 1) 头部
    c.claim(0, min(pe["size_of_headers"], n), "PE_HEADERS")

    # --- 2) 节
    for s in pe["sections"]:
        if s["rawptr"] and s["rawsz"]:
            c.claim(s["rawptr"], s["rawptr"] + s["rawsz"], "SECTION",
                    s["name"])

    # --- 3) 目录
    dirnames = ["EXPORT", "IMPORT", "RESOURCE", "EXCEPTION", "SECURITY",
                "BASERELOC", "DEBUG", "ARCH", "GLOBALPTR", "TLS", "LOADCFG",
                "BOUNDIMP", "IAT", "DELAYIMP", "COM", "RESERVED"]
    for i, (rva, sz) in enumerate(pe["dirs"]):
        if rva and sz and rva < n:
            c.claim(rva, rva + sz, "DIR_" + dirnames[i],
                    "slot%d" % i)

    # --- 4) 所有可打印字符串 (>=4) 的"字面量"字节
    printable = bytes(range(0x20, 0x7F))
    # 快速扫描: 用 re 找 >=6 长度串
    import re
    pat = re.compile(rb"[ -~]{6,}")
    nstr = 0
    strbytes = 0
    for m in pat.finditer(d):
        s, e = m.span()
        got = c.claim(s, e, "ASCII_STRING")
        if got:
            nstr += 1
            strbytes += got
    print("ascii strings>=6: %d runs, %d bytes" % (nstr, strbytes))

    gaps = c.gaps()
    unclassified = sum(e - s for s, e in gaps)
    print("UNCLASSIFIED: %d bytes in %d runs (%.4f%%)"
          % (unclassified, len(gaps), 100.0 * unclassified / n))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "ba00_census.json"), "w",
              encoding="utf-8") as f:
        json.dump(dict(image=IMG, size=n, base=base,
                       pe={k: pe[k] for k in ("image_base", "size_of_image",
                                              "size_of_headers", "dirs")},
                       sections=pe["sections"],
                       regions=c.regions,
                       unclassified_bytes=unclassified,
                       unclassified_runs=len(gaps)), f, indent=1)

    with open(os.path.join(OUT_DIR, "ba00_unclassified.txt"), "w",
              encoding="utf-8") as f:
        big = [(s, e) for s, e in gaps if e - s >= 64]
        big.sort(key=lambda x: -(x[1] - x[0]))
        f.write("# 未归类区间 >=64 字节, 共 %d 段 (未归类总计 %d B)\n"
                % (len(big), unclassified))
        f.write("# file_off   VA          size\n")
        for s, e in big:
            f.write("0x%08X  0x%08X  %8d\n" % (s, s + base, e - s))
    print("wrote DATA/ba00_census.json, DATA/ba00_unclassified.txt")


if __name__ == "__main__":
    main()
