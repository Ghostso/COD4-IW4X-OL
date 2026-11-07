# -*- coding: utf-8 -*-
# Read-only disasm of reference-cited CLIENT-HALF decoder VAs (same build line 1.1.1.13).
import json, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_decoder_va_probe.json"

VAS = {
    "CL_ParseSnapshot@0x49D95F": 0x0049d95f,
    "CL_ParseSnapshot_alt@0x49D95F": 0x0049d95f,
    "CG_TransitionSnapshot@0x45D180": 0x0045d180,
    "nextNoDeltaEntity_inc@0x49CA69": 0x0049ca69,
    "CL_ParseGamestate_cand@0x49C500": 0x0049c500,
    "CL_ParseServerMessage_cand@0x49C5E0": 0x0049c5e0,
    "CL_ParseServerMessage_cand2@0x4A0000": 0x004a0000,
    "CG_SelectWeapon@0x483870": 0x00483870,
    "CG_SetUnlockFlagsFromString@0x468900": 0x00468900,
    "CL_PacketEvent@0x497400": 0x00497400,
    "CL_Netchan_Encode@0x49C586": 0x0049c586,
    "CL_Netchan_Decode@0x49C5E0": 0x0049c5e0,
}

data = open(EXE, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()
pe = pefile.PE(data=data, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
secs = []
for s in pe.sections:
    name = s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((name, ib + s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))

def rva_to_off(rva):
    for name, va, vs, pr, rs in secs:
        base = va - ib
        if base <= rva < base + max(vs, rs):
            return pr + (rva - base)
    return None

md = Cs(CS_ARCH_X86, CS_MODE_32)
out = {"exe": EXE, "sha256": sha, "probes": {}}
for label, va in VAS.items():
    off = rva_to_off(va - ib)
    rec = {"va": "%08x" % va, "off": (hex(off) if off is not None else None)}
    if off is not None:
        code = data[off:off+64]
        rec["hex"] = code.hex()
        rec["disasm"] = ["%08x %-18s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
                         for i in md.disasm(code, va)]
    out["probes"][label] = rec

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for label, rec in out["probes"].items():
    print("=" * 74)
    print(label, "  off", rec["off"])
    for line in rec.get("disasm", [])[:12]:
        print("   ", line)
print("WROTE", OUT)
