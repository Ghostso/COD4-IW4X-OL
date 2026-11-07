import json,io,sys,re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=json.load(open(base+"\\syms_NEW.json",encoding="utf-8")); syms={}
for s in d["symbols"]: syms.setdefault(s["name"],s)
data=open(NEW,"rb").read(); pe=pefile.PE(data=data,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
md=Cs(CS_ARCH_X86, CS_MODE_32)
for name in ["_SV_WriteReliableCommand","_CODOL2697_WriteNativeGamestate"]:
    s=syms[name]; rva=s["rva"]; off=pe.get_offset_from_rva(rva); code=data[off:off+2500*8]
    print("#### %s RVA=%08x VA=%08x"%(name,rva,ib+rva))
    for ins in md.disasm(code,ib+rva):
        if ins.address-ib > rva+0x260: break
        cm=""
        if ins.mnemonic.startswith(("call","jmp")) and ins.op_str.startswith("0x"):
            nm=byrva.get(int(ins.op_str,16)-ib,"")
            if nm: cm="  ; -> %s"%nm
        print("  %08x  %-8s %s%s"%(ins.address,ins.mnemonic,ins.op_str,cm))
    print()
