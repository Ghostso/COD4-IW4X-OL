# -*- coding: utf-8 -*-
# Read-only: find function start containing a VA, then find its callers (E8/E9 + jump-table ptrs).
import json, struct, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_func_start.json"

data = open(EXE, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()
pe = pefile.PE(data=data, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
secs = []
for s in pe.sections:
    name = s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((name, ib + s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))

def va_to_off(va):
    for name, v, vs, pr, rs in secs:
        b = v - ib
        if b <= va - ib < b + max(vs, rs):
            return pr + ((va - ib) - b)
    return None
def off_to_va(off):
    for name, va, vs, pr, rs in secs:
        if pr <= off < pr + rs:
            return va + (off - pr)
    return None

md = Cs(CS_ARCH_X86, CS_MODE_32)

def func_start(va):
    off = va_to_off(va)
    # scan backward for int3 padding then a prologue
    for back in range(0, 0x400):
        o = off - back
        if o < 0: break
        if data[o:o+3] == b"\x55\x8b\xec":  # push ebp; mov ebp,esp
            return off_to_va(o)
    return None

def callers(tgt):
    res = []
    for i in range(len(data)-5):
        if data[i] == 0xE8:
            rel = struct.unpack_from("<i", data, i+1)[0]
            sva = off_to_va(i)
            if sva is not None and (sva+5+rel) & 0xFFFFFFFF == tgt:
                res.append("call %08x" % sva)
        if data[i] == 0xE9:
            rel = struct.unpack_from("<i", data, i+1)[0]
            sva = off_to_va(i)
            if sva is not None and (sva+5+rel) & 0xFFFFFFFF == tgt:
                res.append("jmp  %08x" % sva)
    return res

out = {"exe": EXE, "sha256": sha, "starts": {}}
for label, va in {"CL_ParseSnapshot_body": 0x0049d95f, "nextNoDelta_inc": 0x0049ca69,
                  "CL_PacketEvent_body": 0x0049755b, "CL_Netchan_Decode": 0x0049c5e0}.items():
    fs = func_start(va)
    rec = {"va": "%08x" % va, "func_start": ("%08x" % fs) if fs else None, "callers": []}
    if fs:
        rec["callers"] = callers(fs)
        # also ptr refs
        pat = struct.pack("<I", fs)
        ptrs = []
        st = 0
        while True:
            j = data.find(pat, st)
            if j < 0: break
            ptrs.append("%08x" % off_to_va(j)); st = j+1
        rec["ptr_refs"] = ptrs[:20]
    out["starts"][label] = rec

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for k, v in out["starts"].items():
    print("%-22s va=%s start=%s" % (k, v["va"], v["func_start"]))
    print("    callers:", ", ".join(v["callers"][:15]) or "(none)")
    print("    ptr_refs:", ", ".join(v.get("ptr_refs", [])[:15]) or "(none)")
print("WROTE", OUT)
