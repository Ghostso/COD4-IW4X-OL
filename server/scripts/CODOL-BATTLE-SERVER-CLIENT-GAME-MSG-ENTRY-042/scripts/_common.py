# -*- coding: utf-8 -*-
"""042 helpers for the UNPACKED client EXE image (image_best.bin).
Addressing: file_offset == RVA ; VA = 0x400000 + RVA (proven in 034/verify_target_image)."""
import pefile, struct, capstone, os, hashlib, re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042"
IMG  = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
EV   = os.path.join(ROOT, "evidence")

_b = open(IMG, "rb").read()
_bex = open(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe","rb").read()
pe = pefile.PE(data=_b, fast_load=False)
IB = pe.OPTIONAL_HEADER.ImageBase
SIZE_IMG = pe.OPTIONAL_HEADER.SizeOfImage

def rva2off(r):
    # linear memory image: raw == RVA for the big code sections
    if 0 <= r < len(_b):
        # prefer section-based mapping when raw != va
        for s in pe.sections:
            if s.VirtualAddress <= r < s.VirtualAddress + s.Misc_VirtualSize:
                return s.PointerToRawData + (r - s.VirtualAddress)
        return r
    return None

def raw(r, n):
    o=rva2off(r)
    return _b[o:o+n] if o is not None else None

def rd32(r):
    o=rva2off(r); return struct.unpack("<I", _b[o:o+4])[0] if o is not None else None

def cstr(r, ml=200):
    o=rva2off(r)
    if o is None: return None
    e=_b.find(b"\0",o,o+ml)
    if e<0: e=o+ml
    return _b[o:e]

def sec_of_rva(r):
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.Name.rstrip(b"\0").decode("latin1")
    return "?"

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def dis_at(r, nbytes=15):
    o=rva2off(r)
    if o is None: return None
    for i in md.disasm(_b[o:o+nbytes], IB+r):
        return i
    return None

def dis_range(r, end):
    o=rva2off(r); e=rva2off(end)
    if o is None or e is None: return []
    return list(md.disasm(_b[o:e], IB+r))

def target_of(ins):
    if ins is None: return None
    op=ins.op_str
    if op.startswith("0x"):
        try: return int(op,16)
        except Exception: return None
    return None
