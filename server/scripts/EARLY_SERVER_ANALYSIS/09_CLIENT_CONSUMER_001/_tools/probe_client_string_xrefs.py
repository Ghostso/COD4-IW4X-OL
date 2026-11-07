# -*- coding: utf-8 -*-
# Read-only raw xref scan using CORRECT VAs (the prior 09_C table used file offsets).
import json, struct, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_string_xrefs.json"

STRINGS = {
    "netchan_established": 0x00c489ac,
    "received_gamestate":  0x00c49238,
    "parse_begin":         0x00c49358,
    "parse_badcmd":        0x00c49388,
    "parse_badclientnum":  0x00c493b0,
    "configstrings_pct":   0x00c49210,
    "findcs_overflow":     0x00c5d13c,
    "cs_mismatch":         0x00c4933c,
    "getsnapshot_trunc":   0x00c46370,
    "nonbaseline_discard": 0x00c48f70,
    "awaiting_gamestate":  0x00c6b724,
    "illegible":           0x00c481d8,
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
out = {"exe": EXE, "sha256": sha, "strings": {}}
for label, va in STRINGS.items():
    pat = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0: break
        hits.append(i); start = i + 1
    rec = {"va": "%08x" % va, "raw_occurrences": len(hits), "sites": []}
    for off in hits:
        site_va = off_to_va(off)
        # disasm a window ending at the reference to show the push/mov
        win_off = max(0, off - 24)
        code = data[win_off:off+4]
        dis = []
        for ins in md.disasm(code, (site_va or 0) - (off - win_off)):
            dis.append("%08x %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        rec["sites"].append({
            "off": hex(off),
            "site_va": ("%08x" % site_va) if site_va is not None else None,
            "disasm_window": dis,
        })
    out["strings"][label] = rec

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for label, rec in out["strings"].items():
    print("%-22s va=%s  occurrences=%d" % (label, rec["va"], rec["raw_occurrences"]))
    for s in rec["sites"][:6]:
        tail = s["disasm_window"][-2:] if s["disasm_window"] else []
        print("     site_va=%s" % s["site_va"])
        for d in tail: print("        ", d)
print("WROTE", OUT)
