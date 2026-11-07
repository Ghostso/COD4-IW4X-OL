import json,io,sys,bisect
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8")); m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
syms=load("syms_NEW.json")
d=open(NEW,"rb").read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86, CS_MODE_32)
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva): return byrva.get(rva,"")
def dump(name,start_off_ins=0,maxins=400):
    s=syms[name]; rva=s["rva"]; off=pe.get_offset_from_rva(rva)
    code=d[off:off+maxins*8]
    n=0
    for ins in md.disasm(code,ib+rva):
        if n<start_off_ins: n+=1; continue
        cm=""
        if ins.mnemonic.startswith(("call","jmp")) and ins.op_str.startswith("0x"):
            nm=nameat(int(ins.op_str,16)-ib)
            if nm: cm="  ; -> %s"%nm
        print("  %08x  %-8s %s%s"%(ins.address,ins.mnemonic,ins.op_str,cm)); n+=1
        if n>=maxins: break
print("### _SV_WriteReliableCommand (full)")
dump("_SV_WriteReliableCommand",0,80)
print()
print("### _CODOL_WriteGamestate (tail)")
dump("_CODOL_WriteGamestate",20,90)
