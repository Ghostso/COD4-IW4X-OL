# -*- coding: utf-8 -*-
"""043 audit helpers (read-only)."""
import pefile, struct, capstone, os, hashlib, io

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043"
WS   = r"D:\BaiduNetdiskDownload\使命召唤OL"
EV   = os.path.join(ROOT, "evidence")

DLL  = os.path.join(WS, r"COD OL\codoMP_client_shipRetailBase.dll")
EXE  = os.path.join(WS, r"COD OL\codoMP_client_shipRetail.exe")
IMG  = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

# --- target DLL ---
_b = open(DLL, "rb").read()
pe = pefile.PE(data=_b, fast_load=False)
IB = pe.OPTIONAL_HEADER.ImageBase
SECTIONS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
                 vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData) for s in pe.sections]
def rva2off(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            o = s["raw"] + (r - s["va"])
            return o if 0 <= o < len(_b) else None
    return None
def raw(r, n):
    o = rva2off(r); return _b[o:o+n] if o is not None else None
def cstr(r, ml=200):
    o = rva2off(r)
    if o is None: return None
    e = _b.find(b"\0", o, o+ml)
    if e < 0: e = o+ml
    return _b[o:e]
def sec_of_rva(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]): return s["name"]
    return "?"
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
def dis_at(r, n=15):
    o = rva2off(r)
    if o is None: return None
    for i in md.disasm(_b[o:o+n], IB+r): return i
    return None
def dis_range(r, end):
    o = rva2off(r); e = rva2off(end)
    if o is None or e is None: return []
    return list(md.disasm(_b[o:e], IB+r))
def target_of(ins):
    if ins is None: return None
    op = ins.op_str
    if op.startswith("0x"):
        try: return int(op, 16)
        except Exception: return None
    return None

# --- on-disk EXE bytes ---
_bex = open(EXE, "rb").read()

# --- recovered EXE image (file_offset == RVA, ImageBase 0x400000) ---
_bi = open(IMG, "rb").read()
pe_i = pefile.PE(data=_bi, fast_load=False)
IBI = pe_i.OPTIONAL_HEADER.ImageBase

def iraw(r, n):
    o = r
    return _bi[o:o+n] if 0 <= o and o+n <= len(_bi) else None
def icstr(r, ml=200):
    if r >= len(_bi): return None
    e = _bi.find(b"\0", r, r+ml)
    if e < 0: e = r+ml
    return _bi[r:e]
def idis_at(r, n=15):
    return next(md.disasm(_bi[r:r+n], IBI+r), None)
def idis_range(r, end):
    return list(md.disasm(_bi[r:end], IBI+r))
