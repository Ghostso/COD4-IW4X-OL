# -*- coding: utf-8 -*-
import json, hashlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
VAS = [0x49755b, 0x49c586, 0x49c5e0, 0x5d82bb, 0x5d8241, 0x5d8354, 0x5a0131, 0x4787cb, 0x6d36ab8]
data = open(EXE,"rb").read()
sha = hashlib.sha256(data).hexdigest().upper()
pe = pefile.PE(data=data, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
secs=[]
for s in pe.sections:
    secs.append((s.Name.rstrip(b"\x00").decode("latin1"), ib+s.VirtualAddress, max(s.Misc_VirtualSize, s.SizeOfRawData), s.PointerToRawData))
def r2o(rva):
    for n,va,vs,pr in secs:
        b=va-ib
        if b<=rva<b+vs: return pr+(rva-b)
    return None
md=Cs(CS_ARCH_X86,CS_MODE_32)
out={}
for va in VAS:
    rva=va-ib; off=r2o(rva); rec={"va":hex(va),"off":(hex(off) if off is not None else None)}
    if off is not None:
        code=data[off:off+32]
        rec["disasm"]=["%08x %-18s %s"%(i.address,i.bytes.hex(),i.mnemonic+" "+i.op_str) for i in md.disasm(code,va)]
    out[hex(va)]=rec
json.dump(out, open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_c1va_probe.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK")
