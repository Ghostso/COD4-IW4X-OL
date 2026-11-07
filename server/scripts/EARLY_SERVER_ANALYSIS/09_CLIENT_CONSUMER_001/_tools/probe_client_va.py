# -*- coding: utf-8 -*-
# Independent re-disassembly of server-cited client VAs (read-only).
import json, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
VAS = [0x49dd7e, 0x49d9ce, 0x5a0510, 0x465f57, 0x465bc1, 0x465c27, 0x465c00, 0x46d170, 0x46dea0, 0x46e6a0, 0x471e90, 0x515c90]

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
out = {"exe": EXE, "sha256": sha, "size": len(data), "imagebase": hex(ib), "sections": secs, "probes": {}}
for va in VAS:
    rva = va - ib
    off = rva_to_off(rva)
    rec = {"va": hex(va), "rva": hex(rva), "off": (hex(off) if off is not None else None)}
    if off is not None:
        code = data[off:off+48]
        rec["hex"] = code.hex()
        rec["disasm"] = ["%08x %-20s %s" % (i.address, i.bytes.hex(), i.mnemonic + " " + i.op_str) for i in md.disasm(code, va)]
    out["probes"][hex(va)] = rec

with open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_va_probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("OK", sha)
