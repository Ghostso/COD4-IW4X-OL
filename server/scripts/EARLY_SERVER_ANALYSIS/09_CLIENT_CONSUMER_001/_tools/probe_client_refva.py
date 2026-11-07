# -*- coding: utf-8 -*-
# Read-only re-disassembly of reference-cited (protocol_map.md / ERRORS.md) client VAs
# against THIS client sample. No execution of the sample; static PE parse + capstone only.
import json, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_refva_probe.json"

# VAs cited by the reference build (protocol_map.md / ERRORS.md), i.e. "C1.exe UNPACKED"
VAS = [0x0049c586, 0x0049c5e0, 0x005a0131, 0x0049755b, 0x005d82bb, 0x005d8354,
       0x005d8241, 0x005d5630, 0x005a2821, 0x00497515, 0x00497533, 0x00468900]

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
out = {"exe": EXE, "sha256": sha, "size": len(data), "imagebase": hex(ib), "probes": {}}
for va in VAS:
    off = rva_to_off(va - ib)
    rec = {"va": "%08x" % va, "off": (hex(off) if off is not None else None)}
    if off is not None:
        code = data[off:off+48]
        rec["hex"] = code.hex()
        rec["disasm"] = ["%08x %-18s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
                         for i in md.disasm(code, va)]
    out["probes"]["%08x" % va] = rec

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for k, v in out["probes"].items():
    print("=" * 68)
    print("VA", k, "off", v["off"])
    for line in v.get("disasm", []):
        print("  ", line)
print("WROTE", OUT)
