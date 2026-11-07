# -*- coding: utf-8 -*-
"""044 static-closure helpers (STRICTLY READ-ONLY).

Reads only:
  - COD OL\codoMP_client_shipRetail.exe            (S-EXE, packed on-disk)
  - COD OL\codoMP_client_shipRetailBase.dll        (S-DLL, packed .tvm0/.tls)
  - CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin  (S-IMG, recovered)
Never writes outside ROOT. Never launches, injects, hooks or dumps.
"""
import pefile, struct, capstone, os, hashlib, json

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-STATIC-CLOSURE-044"
WS   = r"D:\BaiduNetdiskDownload\使命召唤OL"
EV   = os.path.join(ROOT, "evidence")
os.makedirs(EV, exist_ok=True)

DLL  = os.path.join(WS, r"COD OL\codoMP_client_shipRetailBase.dll")
EXE  = os.path.join(WS, r"COD OL\codoMP_client_shipRetail.exe")
IMG  = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def w(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

# ---------- on-disk EXE (packed) ----------
_bex = open(EXE, "rb").read()
pe_exe = pefile.PE(data=_bex, fast_load=False)
EXE_IB = pe_exe.OPTIONAL_HEADER.ImageBase
EXE_SECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
                 vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
            for s in pe_exe.sections]

# ---------- on-disk DLL (packed) ----------
_bdl = open(DLL, "rb").read()
pe_dll = pefile.PE(data=_bdl, fast_load=False)
DLL_IB = pe_dll.OPTIONAL_HEADER.ImageBase
DLL_SECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
                 vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
            for s in pe_dll.sections]

# ---------- recovered EXE image: file_offset == RVA, ImageBase 0x400000 ----------
_bi = open(IMG, "rb").read()
pe_img = pefile.PE(data=_bi, fast_load=False)
IMG_IB = pe_img.OPTIONAL_HEADER.ImageBase
IMG_SECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
                 vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
            for s in pe_img.sections]
IMG_LEN = len(_bi)

def img_section_of(rva):
    for s in IMG_SECS:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            return s
    return None

def img_in_file(rva, n=1):
    """True only if [rva, rva+n) is inside the *file-backed* (present) part of the image."""
    if rva < 0 or rva + n > IMG_LEN:
        return False
    s = img_section_of(rva)
    if s is None:
        return False
    # present bytes = raw .. raw+rsize (004/043 established file_off==RVA)
    return s["raw"] <= rva and rva + n <= s["raw"] + s["rsize"]

def iraw(rva, n):
    return _bi[rva:rva + n] if img_in_file(rva, n) else None

def idword(rva):
    b = iraw(rva, 4)
    return struct.unpack("<I", b)[0] if b else None

def icstr(rva, ml=300):
    if not img_in_file(rva, 1):
        return None
    e = _bi.find(b"\0", rva, rva + ml)
    if e < 0:
        e = rva + ml
    return _bi[rva:e]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def idis_at(rva, n=15):
    if not img_in_file(rva, n):
        return None
    return next(md.disasm(_bi[rva:rva + n], IMG_IB + rva), None)

def idis_range(rva, end):
    if not img_in_file(rva, max(1, end - rva)):
        # clip to present region
        s = img_section_of(rva)
        if s is None:
            return []
        end = min(end, s["raw"] + s["rsize"])
    return list(md.disasm(_bi[rva:end], IMG_IB + rva))

def linear_disasm(rva, end, stop_on_ret=False):
    """Linear sweep; returns list. Does not follow branches."""
    return idis_range(rva, end)

def func_by_cc(rva, cap=0x20000):
    """Next 0xCC-run or next function prologue heuristic: returns (start,end) around rva."""
    return None

def dword_refs_all(value, lo=0, hi=None):
    """Find all 4-byte LE occurrences of `value` in *present* image bytes."""
    if hi is None:
        hi = IMG_LEN
    pat = struct.pack("<I", value & 0xFFFFFFFF)
    hits = []
    i = lo - 4
    # scan present sections only
    for s in IMG_SECS:
        a = max(lo, s["raw"])
        b = min(hi, s["raw"] + s["rsize"], IMG_LEN)
        if b <= a:
            continue
        blk = _bi[a:b]
        j = blk.find(pat)
        while j >= 0:
            hits.append(a + j)
            j = blk.find(pat, j + 1)
    return hits

def imm32_targets_in_func(rva, end):
    """All direct call/jmp rel32 targets found by linear sweep in [rva,end)."""
    out = []
    for ins in idis_range(rva, end):
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            try:
                t = int(ins.op_str, 16) - IMG_IB
            except ValueError:
                continue
            out.append((ins.address - IMG_IB, ins.mnemonic, t))
    return out

def dis_text(ins):
    return "  %08x  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)

def dump(rva, end, title=None):
    lines = []
    if title:
        lines.append("=== %s RVA=%08x..%08x ===" % (title, rva, end))
    for ins in idis_range(rva, end):
        lines.append(dis_text(ins))
    return "\n".join(lines)