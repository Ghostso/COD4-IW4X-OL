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
start, end = 0x5d0000, 0x5e0000
off=r2o(start-ib); code=data[off:off+(end-start)]
ins=list(md.disasm(code,start))
stores=[]
for i in ins:
    if i.mnemonic=="mov" and "byte ptr" in i.op_str:
        last=i.op_str.split(",")[-1].strip()
        try: imm=int(last,16)
        except: continue
        stores.append((hex(i.address), i.op_str, imm))
json.dump({"range":[hex(start),hex(end)],"byte_stores":stores}, open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_evidence\client_serverhalf_5dwide.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("ins", len(ins), "stores", len(stores))
for s in stores:
    if s[2] in (0,1,2,3,5,6,7): print(s[0], "->", s[2], s[1])
