# -*- coding: utf-8 -*-
"""046 common helpers. STRICTLY READ-ONLY over the recovered image + source artifacts."""
import pefile, struct, capstone, os, hashlib, json, sys

T = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046"
WS = r"D:\BaiduNetdiskDownload\使命召唤OL"
EV = os.path.join(T, "evidence")
X  = os.path.join(T, "_extracted")
os.makedirs(EV, exist_ok=True)

IMG = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
EXE = os.path.join(WS, r"COD OL\codoMP_client_shipRetail.exe")
DLL = os.path.join(WS, r"COD OL\codoMP_client_shipRetailBase.dll")
IB  = 0x400000

_img = open(IMG, "rb").read()
_exe = open(EXE, "rb").read()
pe = pefile.PE(data=_img, fast_load=False)
SECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
             vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
        for s in pe.sections]
IMG_LEN = len(_img)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()

def sec_of(rva):
    for s in SECS:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            return s
    return None

def in_file(rva, n=1):
    if rva < 0 or rva + n > IMG_LEN: return False
    s = sec_of(rva)
    return bool(s) and s["raw"] <= rva and rva + n <= s["raw"] + max(s["rsize"],0)

def raw(rva, n):
    return _img[rva:rva+n] if in_file(rva,n) else None

def d32(rva):
    b = raw(rva,4); return struct.unpack("<I",b)[0] if b else None

def d32_at(buf,off): return struct.unpack_from("<I",buf,off)[0]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def dis(rva, n=15):
    if not in_file(rva,n): return None
    return next(md.disasm(_img[rva:rva+n], IB+rva), None)

def dis_range(rva, end):
    s = sec_of(rva)
    if not s: return []
    end = min(end, s["raw"]+s["rsize"])
    return list(md.disasm(_img[rva:end], IB+rva))

def fmt(ins):
    return "  %08x  %-22s %s %s" % (ins.address-IB, ins.bytes.hex(), ins.mnemonic, ins.op_str)

def dump(rva, end, title=None):
    L=[]
    if title: L.append("=== %s RVA=%08X..%08X ===" % (title, rva, end))
    for i in dis_range(rva,end): L.append(fmt(i))
    return "\n".join(L)

def w(path, text):
    with open(path,"w",encoding="utf-8") as f: f.write(text)
    return path

def e8_callers(target_rva, lo=0x1000, hi=0x8a7000):
    """direct rel32 call sites (E8) and jumps (E9) whose target == target_rva."""
    out=[]
    tva = IB+target_rva
    for i in range(lo, hi-5):
        if _img[i] in (0xE8,0xE9):
            rel = struct.unpack_from("<i", _img, i+1)[0]
            if (IB+i+5+rel) & 0xFFFFFFFF == tva:
                out.append((i, "call" if _img[i]==0xE8 else "jmp"))
    return out

def refs_dword(value):
    pat = struct.pack("<I", value & 0xFFFFFFFF); hits=[]
    i = _img.find(pat)
    while i>=0:
        if any(s["raw"] <= i < s["raw"]+s["rsize"] for s in SECS): hits.append(i)
        i = _img.find(pat, i+1)
    return hits

def abs_mem_operands(lo=0x1000, hi=0x8a7000):
    """scan for 'call dword ptr [imm32]' style indirect calls"""
    out=[]
    for i in range(lo,hi-6):
        if _img[i]==0xFF and _img[i+1] in (0x15,0x25):
            out.append((i, "call" if _img[i+1]==0x15 else "jmp", struct.unpack_from("<I",_img,i+2)[0]))
    return out
