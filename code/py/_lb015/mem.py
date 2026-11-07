# -*- coding: utf-8 -*-
"""Loader for the fresh full linear memory dump (mem_linear_20261007_134406).
Region files named r_XXXXXXXX_YYYY.bin where XXXXXXXX = VA, YYYY = size.
"""
import os, struct, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMPS = [
    r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\mem_linear_20261007_134406",
]

class Mem(object):
    def __init__(self, dirs):
        self.regions = []   # (va, size, bytes)
        for d in dirs:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not (fn.startswith("r_") and fn.endswith(".bin")):
                    continue
                parts = fn.split("_")
                try:
                    va = int(parts[1], 16)
                except Exception:
                    continue
                p = os.path.join(d, fn)
                data = open(p, "rb").read()
                self.regions.append((va, len(data), data))
        self.regions.sort()
        self.starts = [r[0] for r in self.regions]
        self.MD = Cs(CS_ARCH_X86, CS_MODE_32); self.MD.detail = True

    def find(self, va):
        i = bisect.bisect_right(self.starts, va) - 1
        while i >= 0:
            s, sz, data = self.regions[i]
            if s <= va < s + sz:
                return i
            i -= 1
        return -1

    def read(self, va, n):
        i = self.find(va)
        if i < 0:
            return None
        s, sz, data = self.regions[i]
        off = va - s
        if off + n <= sz:
            return data[off:off+n]
        return None

    def byte(self, va):
        r = self.read(va, 1)
        return r[0] if r else None

    def dword(self, va):
        r = self.read(va, 4)
        return struct.unpack("<I", r)[0] if r else None

    def sword(self, va):
        r = self.read(va, 4)
        return struct.unpack("<i", r)[0] if r else None

    def qword(self, va):
        r = self.read(va, 8)
        return struct.unpack("<Q", r)[0] if r else None

    def cstr(self, va, maxn=200):
        r = self.read(va, maxn)
        if r is None:
            return None
        z = r.find(b"\x00")
        if z >= 0:
            r = r[:z]
        return r

    def dis(self, va, count=30, n=None):
        if n is None:
            n = count * 10
        code = self.read(va, n)
        if code is None:
            return []
        return list(self.MD.disasm(code, va))

    def show(self, va, count=30):
        out = []
        for ins in self.dis(va, count=count):
            out.append("  %08X  %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic + " " + ins.op_str))
        return "\n".join(out)

M = Mem(DUMPS)

