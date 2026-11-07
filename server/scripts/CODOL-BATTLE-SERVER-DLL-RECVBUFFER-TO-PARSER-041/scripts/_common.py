# -*- coding: utf-8 -*-
"""041 shared static-analysis helpers (read-only)."""
import pefile, struct, capstone, os, json, hashlib, collections

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041"
DLL  = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
EV   = os.path.join(ROOT, "evidence")

_b = open(DLL, "rb").read()
pe = pefile.PE(data=_b, fast_load=False)
IB = pe.OPTIONAL_HEADER.ImageBase
SECTIONS = []
for s in pe.sections:
    SECTIONS.append(dict(name=s.Name.rstrip(b"\0").decode("latin1"),
        va=s.VirtualAddress, vsize=s.Misc_VirtualSize,
        raw=s.PointerToRawData, rsize=s.SizeOfRawData))

def sec_of_rva(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            return s["name"]
    return "?"

def rva2off(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            o = s["raw"] + (r - s["va"])
            if 0 <= o < len(_b):
                return o
    return None

def off2rva(o):
    for s in SECTIONS:
        if s["raw"] <= o < s["raw"] + s["rsize"]:
            r = s["va"] + (o - s["raw"])
            if 0 <= r:
                return r
    return None

def rd32(rva):
    o = rva2off(rva)
    return struct.unpack("<I", _b[o:o+4])[0] if o is not None else None

def rd16(rva):
    o = rva2off(rva)
    return struct.unpack("<H", _b[o:o+2])[0] if o is not None else None

def rdb(rva):
    o = rva2off(rva)
    return _b[o] if o is not None else None

def raw(rva, n):
    o = rva2off(rva)
    return _b[o:o+n] if o is not None else None

def cstr(rva, maxlen=400):
    o = rva2off(rva)
    if o is None: return None
    e = _b.find(b"\0", o, o+maxlen)
    if e < 0: e = o + maxlen
    return _b[o:e]

def read_hintname(rva):
    o = rva2off(rva)
    if o is None: return None
    hint = struct.unpack("<H", _b[o:o+2])[0]
    e = _b.find(b"\0", o+2)
    return hint, _b[o+2:e]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def dis_at(rva, nbytes=15):
    o = rva2off(rva)
    if o is None: return None
    for i in md.disasm(_b[o:o+nbytes], IB + rva):
        return i
    return None

def dis_range(rva, end_rva):
    o = rva2off(rva); e = rva2off(end_rva)
    if o is None or e is None: return []
    return list(md.disasm(_b[o:e], IB + rva))

def dis_n(rva, n):
    o = rva2off(rva)
    if o is None: return []
    return list(md.disasm(_b[o:o+n], IB + rva))

# ---- whole-.text byte scan for call/jmp rel32 and FF15 ----
_text = [s for s in SECTIONS if s["name"] == ".text"][0]
_td = _b[_text["raw"]: _text["raw"]+_text["rsize"]]

def _scan(op_bytes):
    hits = []; i = 0; n = len(_td) - 4
    first = op_bytes[0]
    while i < n:
        if _td[i] == first:
            if len(op_bytes) == 1 or _td[i+1] == op_bytes[1]:
                hits.append(_text["va"] + i)
                i += len(op_bytes)
                continue
        i += 1
    return hits

def scan_ff15():
    out = []
    for va in _scan(b"\xff\x15"):
        ins = dis_at(va)
        if ins and ins.mnemonic == "call" and ins.op_str.startswith("dword ptr ["):
            out.append(ins)
    return out

def scan_call_rel32():
    out = []
    for va in _scan(b"\xe8"):
        ins = dis_at(va)
        if ins and ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            out.append(ins)
    return out

def scan_jmp_rel32():
    out = []
    for va in _scan(b"\xe9"):
        ins = dis_at(va)
        if ins and ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            out.append(ins)
    return out

def target_of(ins):
    if ins is None: return None
    op = ins.op_str
    if op.startswith("0x"):
        try: return int(op, 16)
        except Exception: return None
    return None

def func_padding_before(rva):
    """scan backwards for >=2 consecutive 0xCC (int3) padding; return rva of first byte after padding."""
    o = rva2off(rva)
    if o is None: return rva
    i = o - 1
    seen = 0
    while i >= 0 and seen < 64:
        if _b[i] in (0xCC, 0x90):
            i -= 1; seen += 1
        else:
            break
    if seen >= 1:
        return off2rva(i+1)
    return rva
