# -*- coding: utf-8 -*-
"""Shared PE helper for E-24. All RVAs; VA = RVA + 0x400000."""
import struct, pefile
from capstone import *

P = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
IB = 0x400000

class Img:
    def __init__(self, path=P):
        self.pe = pefile.PE(path, fast_load=True)
        self.IB = self.pe.OPTIONAL_HEADER.ImageBase
        self.d = open(path, "rb").read()
        self.secs = [(s.Name.rstrip(b"\0").decode(errors="replace"), s.VirtualAddress,
                      s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData,
                      bool(s.Characteristics & 0x20000000)) for s in self.pe.sections]
        self.md = Cs(CS_ARCH_X86, CS_MODE_32); self.md.detail = True
    def sec(self, rva):
        for n, va, vs, rp, rs, x in self.secs:
            if va <= rva < va + vs: return n
        return None
    def off(self, rva):
        for n, va, vs, rp, rs, x in self.secs:
            if va <= rva < va + vs:
                return rp + rva - va if (rs and rva - va < rs) else None
        return None
    def bytes(self, rva, n):
        o = self.off(rva)
        return self.d[o:o+n] if o is not None else None
    def u32(self, rva):
        b = self.bytes(rva, 4)
        return struct.unpack("<I", b)[0] if b else None
    def rd(self, va, n):
        return self.bytes(va - self.IB, n)
    def dis(self, rva, n):
        o = self.off(rva)
        if o is None: return []
        return list(self.md.disasm(self.d[o:o+n], self.IB + rva))

def call_targets(img):
    """Return dict target_VA -> [caller_RVA...] for all E8/E9 rel32 in .text."""
    n, va, vs, rp, rs, x = [s for s in img.secs if s[0] == ".text"][0]
    data = img.d[rp:rp+rs]
    out = {}
    for i in range(len(data) - 5):
        if data[i] in (0xe8, 0xe9):
            rel = struct.unpack_from("<i", data, i+1)[0]
            tgt = (img.IB + va + i + 5 + rel) & 0xffffffff
            out.setdefault(tgt, []).append((va + i, data[i]))
    return out

def find_calls(img, callmap, rva):
    return callmap.get((img.IB + rva) & 0xffffffff, [])

def dump(img, rva, n, out, tag=""):
    out.write("="*76 + "\n%s RVA %06X VA %08X sec=%s\n" % (tag, rva, img.IB+rva, img.sec(rva)))
    ins = img.dis(rva, n)
    if not ins: out.write("NO_RAW\n"); return
    for i in ins:
        out.write("%06X %-22s %s %s\n" % (i.address - img.IB, bytes(i.bytes).hex(), i.mnemonic, i.op_str))

def func_start(img, rva, floor=0x1000):
    """Walk back over int3 padding, then to previous ret-terminated boundary."""
    j = rva
    o = img.off(j)
    while j > floor and img.d[img.off(j)-1] == 0xcc:
        j -= 1
    return j

if __name__ == "__main__":
    im = Img()
    print("ImageBase", hex(im.IB), "SizeOfImage", hex(im.pe.OPTIONAL_HEADER.SizeOfImage))
    for s in im.secs: print("  ", s)
