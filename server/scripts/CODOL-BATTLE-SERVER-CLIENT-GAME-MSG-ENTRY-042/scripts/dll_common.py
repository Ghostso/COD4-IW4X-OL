# -*- coding: utf-8 -*-
"""042 DLL/EXE-bound helper used by the exploratory scripts s01..s16.
Read-only. Targets codoMP_client_shipRetailBase.dll (ImageBase 0x10000000)
and codoMP_client_shipRetail.exe (ImageBase 0x400000)."""
import pefile, struct, capstone, os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042"
DLL  = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
EXE  = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
EV   = os.path.join(ROOT, "evidence")

_b   = open(DLL, "rb").read()
_bex = open(EXE, "rb").read()
pe = pefile.PE(data=_b, fast_load=False)
IB = pe.OPTIONAL_HEADER.ImageBase
SECTIONS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
                 vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData) for s in pe.sections]

def sec_of_rva(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]): return s["name"]
    return "?"

def rva2off(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            o = s["raw"] + (r - s["va"])
            if 0 <= o < len(_b): return o
    return None

def off2rva(o):
    for s in SECTIONS:
        if s["raw"] <= o < s["raw"] + s["rsize"]: return s["va"] + (o - s["raw"])
    return None

def rd32(r):
    o = rva2off(r); return struct.unpack("<I", _b[o:o+4])[0] if o is not None else None
def rd16(r):
    o = rva2off(r); return struct.unpack("<H", _b[o:o+2])[0] if o is not None else None
def rdb(r):
    o = rva2off(r); return _b[o] if o is not None else None
def raw(r, n):
    o = rva2off(r); return _b[o:o+n] if o is not None else None
def cstr(r, maxlen=400):
    o = rva2off(r)
    if o is None: return None
    e = _b.find(b"\0", o, o+maxlen)
    if e < 0: e = o + maxlen
    return _b[o:e]
def read_hintname(r):
    o = rva2off(r)
    if o is None: return None
    e = _b.find(b"\0", o+2)
    return struct.unpack("<H", _b[o:o+2])[0], _b[o+2:e]

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
def dis_n(r, n):
    o = rva2off(r); return list(md.disasm(_b[o:o+n], IB+r)) if o is not None else []
def target_of(ins):
    if ins is None: return None
    op = ins.op_str
    if op.startswith("0x"):
        try: return int(op, 16)
        except Exception: return None
    return None

_text = [s for s in SECTIONS if s["name"] == ".text"][0]
_td = _b[_text["raw"]: _text["raw"]+_text["rsize"]]
def _scan(op_bytes):
    hits=[]; i=0; n=len(_td)-4; first=op_bytes[0]
    while i<n:
        if _td[i]==first and (len(op_bytes)==1 or _td[i+1]==op_bytes[1]):
            hits.append(_text["va"]+i); i+=len(op_bytes); continue
        i+=1
    return hits
def scan_ff15():
    out=[]
    for va in _scan(b"\xff\x15"):
        ins=dis_at(va)
        if ins and ins.mnemonic=="call" and ins.op_str.startswith("dword ptr ["): out.append(ins)
    return out
def scan_call_rel32():
    out=[]
    for va in _scan(b"\xe8"):
        ins=dis_at(va)
        if ins and ins.mnemonic=="call" and ins.op_str.startswith("0x"): out.append(ins)
    return out
def scan_jmp_rel32():
    out=[]
    for va in _scan(b"\xe9"):
        ins=dis_at(va)
        if ins and ins.mnemonic=="jmp" and ins.op_str.startswith("0x"): out.append(ins)
    return out
