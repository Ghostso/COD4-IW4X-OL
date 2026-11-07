# -*- coding: utf-8 -*-
# Read-only: locate references (4-byte LE) to key client parser VAs (jump tables, pointers).
import json, struct, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_parser_ptr_refs.json"

TARGETS = {
    "CL_ParseSnapshot@0x49D95F": 0x0049d95f,
    "CL_PacketEvent@0x497400": 0x00497400,
    "nextNoDelta_inc@0x49CA69": 0x0049ca69,
    "CL_Netchan_Encode@0x49C586": 0x0049c586,
}

data = open(EXE, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()
pe = pefile.PE(data=data, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
secs = []
for s in pe.sections:
    name = s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((name, ib + s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))

def off_to_va(off):
    for name, va, vs, pr, rs in secs:
        if pr <= off < pr + rs:
            return va + (off - pr)
    return None

md = Cs(CS_ARCH_X86, CS_MODE_32)
out = {"exe": EXE, "sha256": sha, "targets": {}}
for label, tgt in TARGETS.items():
    pat = struct.pack("<I", tgt)
    hits = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0: break
        hits.append(i); start = i + 1
    rec = {"target": "%08x" % tgt, "count": len(hits), "sites": []}
    for off in hits:
        site_va = off_to_va(off)
        # check if it looks like a jump-table neighborhood: disasm a window before
        win = data[max(0, off-16):off+4]
        dis = ["%08x %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
               for ins in md.disasm(win, (site_va or 0) - (off - max(0, off-16)))]
        rec["sites"].append({"off": hex(off), "site_va": ("%08x" % site_va) if site_va else None, "dis": dis[-3:]})
    out["targets"][label] = rec

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for label, rec in out["targets"].items():
    print("%-32s count=%d" % (label, rec["count"]))
    for s in rec["sites"][:10]:
        print("    site_va=%s off=%s" % (s["site_va"], s["off"]))
        for d in s["dis"]: print("        ", d)
print("WROTE", OUT)
