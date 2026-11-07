# -*- coding: utf-8 -*-
import json
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data = open(EXE,"rb").read()
pe = pefile.PE(data=data, fast_load=True); ib = pe.OPTIONAL_HEADER.ImageBase
secs=[(s.Name.rstrip(b"\x00").decode("latin1"), ib+s.VirtualAddress, max(s.Misc_VirtualSize,s.SizeOfRawData), s.PointerToRawData) for s in pe.sections]
def r2o(rva):
    for n,va,vs,pr in secs:
        b=va-ib
        if b<=rva<b+vs: return pr+(rva-b)
    return None
md=Cs(CS_ARCH_X86,CS_MODE_32)
start, end = 0x5d8000, 0x5d8370
off=r2o(start-ib); code=data[off:off+(end-start)]
lines=["%08x %-22s %s"%(i.address,i.bytes.hex(),i.mnemonic+" "+i.op_str) for i in md.disasm(code,start)]
open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_serverhalf_5d8000_5d8370.asm.txt","w",encoding="utf-8").write("\n".join(lines))
print(len(lines),"lines")
