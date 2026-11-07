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
text=[s for s in pe.sections if s.Name.rstrip(b"\x00")==b".text"][0]
tbody=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]; tbase=ib+text.VirtualAddress
funcs=sorted([(v["rva"],k) for k,v in syms.items() if v["section"]==".text"]); starts=[f[0] for f in funcs]
def owner(rva):
    i=bisect.bisect_right(starts,rva)-1
    return funcs[i][1] if i>=0 else None
# find instructions referencing each VA via immediate push/mov
def who(idt, va):
    res=[]
    for ins in md.disasm(tbody,tbase):
        if ins.op_str and ("0x%x"%va) in ins.op_str:
            res.append((ins.address-ib,owner(ins.address-ib),ins.mnemonic,ins.op_str))
    return res
for va in [0x7c424c,0x7edee0,0x7c419c,0x7c416c]:
    print("VA %#x"%va)
    for r,o,m,os in who(d,va): print("    %#010x %-40s %s %s"%(r,o,m,os))
    print()
