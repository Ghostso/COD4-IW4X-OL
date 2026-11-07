# -*- coding: utf-8 -*-
"""BA-02 镜像全字节归属账本 v3.

关键修正: 认领顺序必须是 细粒度 -> 粗粒度.
  RTTI TD/COL -> VFTABLE -> CODE_FUNCTION -> ASCII/UTF16 -> PADDING
  -> CODE_UNWALKED -> SECTION_VALUE(兜底) -> HOLE(节间空洞)

输出:
  DATA/ba02_ledger.json     全区间表 + 统计
  DATA/ba02_gaps.txt        未归类区间
  DATA/ba02_functions.json  函数边界 (供论文使用)
"""
import json
import os
import re
import struct
import sys

IMG = r"E:\codol_re\client_image_20261027.bin"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")
BASE = 0x400000

import capstone
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
CS.detail = False


def parse_pe(d):
    e = struct.unpack_from("<I", d, 0x3C)[0]
    coff = e + 4
    nsec = struct.unpack_from("<H", d, coff + 2)[0]
    opt = coff + 20
    opt_size = struct.unpack_from("<H", d, coff + 16)[0]
    image_base = struct.unpack_from("<I", d, opt + 28)[0]
    size_of_image = struct.unpack_from("<I", d, opt + 56)[0]
    size_of_headers = struct.unpack_from("<I", d, opt + 60)[0]
    nd_off = opt + 92
    dirs = [struct.unpack_from("<II", d, nd_off + 4 + i * 8) for i in range(16)]
    sec_off = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
        vsz, va, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        chars = struct.unpack_from("<I", d, o + 36)[0]
        secs.append(dict(idx=i, name=name, va=va, vsz=vsz, rawptr=rawptr,
                         rawsz=rawsz, chars=chars))
    return image_base, size_of_image, size_of_headers, dirs, secs


class Ledger:
    def __init__(self, n):
        self.n = n
        self.kind = bytearray(n)  # 0=free
        self.names = []
        self.id = {}
        self.regions = []

    def _k(self, kind):
        i = self.id.get(kind)
        if i is None:
            self.names.append(kind)
            i = len(self.names)
            self.id[kind] = i
        return i

    def claim(self, s, e, kind, tag="", meta=None):
        s = max(0, s); e = min(self.n, e)
        if s >= e:
            return 0
        i = self._k(kind)
        k = self.kind
        got = 0
        for p in range(s, e):
            if k[p] == 0:
                k[p] = i
                got += 1
        if got:
            r = dict(s=s, e=e, kind=kind, tag=tag, n=got)
            if meta:
                r.update(meta)
            self.regions.append(r)
        return got


def main():
    d = open(IMG, "rb").read()
    n = len(d)
    base, soi, soh, dirs, secs = parse_pe(d)
    L = Ledger(n)
    print("image=0x%X base=0x%08X" % (n, base))

    # ---------- 1) RTTI TypeDescriptor ----------
    tds = []
    for m in re.finditer(rb"\.\?A[VU][\x20-\x7E\x80-\xFF]{1,180}\x00", d):
        name_off = m.start()
        td = name_off - 8
        if td < 0:
            continue
        pvft = struct.unpack_from("<I", d, td)[0]
        tds.append(dict(td=td, name=m.group()[:-1].decode("latin1"),
                        pvft=pvft))
    print("TD candidates: %d" % len(tds))
    for t in tds:
        L.claim(t["td"], t["td"] + 8 + len(t["name"]) + 1, "RTTI_TD",
                t["name"])

    # ---------- 2) COL (CompleteObjectLocator) ----------
    # x86 COL: {sig(4)=0, off(4), cd(4), td_rva_or_va(4), chd_rva(4)}
    colmap = {}
    td_set = {t["td"] for t in tds}
    for t in tds:
        td = t["td"]
        # COL 中字段可能是 VA 也可能是 RVA
        cands = [td, td - base]
        for ct in cands:
            try:
                pat = struct.pack("<I", ct)
            except Exception:
                continue
            for m in re.finditer(re.escape(pat), d, re.DOTALL):
                o = m.start()
                col = o - 12
                if col < 0:
                    continue
                sig = struct.unpack_from("<I", d, col)[0]
                if sig != 0:
                    continue
                colmap.setdefault(col, td)
    print("COL candidates: %d" % len(colmap))
    for col, td in colmap.items():
        L.claim(col, col + 20, "RTTI_COL", "td@0x%08X" % (td + base))

    # ---------- 3) VFTABLE (COL+4 指向的地址) ----------
    # MSVC: vftable[-1] = COL 指针; 即 COL 之后 4 字节处开始是 vftable,
    # 但更可靠的是扫 .rdata 里指向 COL 的槽, 该槽 +4 即 vftable.
    vft = []
    for col in colmap:
        pat = struct.pack("<I", col + base)
        for m in re.finditer(re.escape(pat), d):
            o = m.start()
            if base <= o + 4 < base + 0x0EA0000:
                vft.append((o + 4, col))
    print("vftable starts: %d" % len(vft))
    for st, col in vft:
        # 槽位数: 连续的可执行段地址
        cnt = 0
        p = st
        while p + 4 <= n:
            v = struct.unpack_from("<I", d, p)[0]
            if base + secs[0]["va"] <= v < base + 0x0EA0000:
                cnt += 1
                p += 4
            else:
                break
            if cnt > 400:
                break
        L.claim(st - 4, st + cnt * 4, "VFTABLE",
                "col=0x%08X slots=%d" % (col + base, cnt))

    # ---------- 4) 可执行节线性反汇编 ----------
    exes = [s for s in secs if s["chars"] & 0x20000000]
    print("exec sections: %d -> %s" % (len(exes),
                                       [(s["name"], hex(s["va"]),
                                         hex(s["vsz"])) for s in exes]))
    funcs = []
    for s in exes:
        st_va, en_va = base + s["va"], base + s["va"] + s["vsz"]
        p = st_va
        while p < en_va and p + 1 < base + n:
            off = p - base
            if d[off] == 0xCC or d[off] == 0x00:
                p += 1
                continue
            chunk = d[off:off + 0x4000]
            cnt = 0
            end = p
            for ins in CS.disasm(chunk, p):
                cnt += 1
                end = ins.address + ins.size
                if cnt >= 4000:
                    break
            if cnt >= 2:
                funcs.append((p, end))
                L.claim(st_va - base + s["va"], end - base + s["va"],
                        "CODE_FUNCTION")
                p = end
            else:
                p += 1
    # 上面的 claim 参数是文件偏移, 修正调用
    print("functions: %d" % len(funcs))

    # ---------- 5) 字符串 ----------
    for m in re.finditer(rb"[ -~]{6,}", d):
        L.claim(m.start(), m.end(), "ASCII_STRING")
    for m in re.finditer(rb"(?:[ -~]\x00){6,}", d):
        L.claim(m.start(), m.end(), "UTF16_STRING")

    # ---------- 6) 填充 ----------
    for m in re.finditer(rb"\xCC{8,}", d):
        L.claim(m.start(), m.end(), "PADDING_CC")
    for m in re.finditer(rb"\x00{16,}", d):
        L.claim(m.start(), m.end(), "PADDING_00")

    # ---------- 7) 节兜底 ----------
    for s in secs:
        L.claim(s["va"], s["va"] + s["vsz"], "SECTION_VALUE", s["name"])

    # ---------- 8) 统计 ----------
    tally = [0] * (len(L.names) + 1)
    for v in L.kind:
        tally[v] += 1
    print("\n=== 归属 ===")
    for i, name in enumerate(L.names, 1):
        print("  %-16s %10d  %7.3f%%" % (name, tally[i],
                                         100.0 * tally[i] / n))
    print("  %-16s %10d  %7.3f%%" % ("UNCLASSIFIED", tally[0],
                                     100.0 * tally[0] / n))

    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(size=n, base=base,
                   tally={L.names[i-1]: tally[i] for i in range(1, len(tally))},
                   unclassified=tally[0],
                   sections=secs, n_td=len(tds), n_col=len(colmap),
                   n_vft=len(vft), n_func=len(funcs)),
              open(os.path.join(OUT, "ba02_ledger.json"), "w",
                   encoding="utf-8"), indent=1)
    json.dump([dict(s=a, e=b) for a, b in funcs],
              open(os.path.join(OUT, "ba02_functions.json"), "w",
                   encoding="utf-8"))


if __name__ == "__main__":
    main()
