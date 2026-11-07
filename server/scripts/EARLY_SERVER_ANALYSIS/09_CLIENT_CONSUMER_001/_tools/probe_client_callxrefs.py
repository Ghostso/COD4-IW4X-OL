# -*- coding: utf-8 -*-
# Read-only call-xref scan (E8 rel32) to find callers of known client functions.
import json, struct, hashlib
import pefile

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_callxrefs.json"

TARGETS = {
    "CL_ParseSnapshot@0x49D95F": 0x0049d95f,
    "CL_Netchan_Decode@0x49C5E0": 0x0049c5e0,
    "CL_Netchan_Encode@0x49C586": 0x0049c586,
    "CG_TransitionSnapshot@0x45D180": 0x0045d180,
    "nextNoDelta_inc@0x49CA69": 0x0049ca69,
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

out = {"exe": EXE, "sha256": sha, "targets": {}}
for label, tgt in TARGETS.items():
    calls = []
    for i in range(len(data) - 5):
        if data[i] == 0xE8:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            site_va = off_to_va(i)
            if site_va is None: continue
            if (site_va + 5 + rel) & 0xFFFFFFFF == tgt:
                calls.append("%08x" % site_va)
    out["targets"][label] = {"target": "%08x" % tgt, "callers": calls}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for label, rec in out["targets"].items():
    print("%-32s callers(%d): %s" % (label, len(rec["callers"]), ", ".join(rec["callers"][:20])))
print("WROTE", OUT)
