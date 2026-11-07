import json,pefile
from capstone import *
sym=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding="utf-8"))
want={"_SV_WriteReliableCommand","_SV_ProfileCommand2697","_CODOL2697_ProfileCommandBytes"}
rvas={s["name"]:int(s["rva"]) for s in sym["symbols"] if s["name"] in want and s.get("section")==".text"}
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86, CS_MODE_32)
for k in sorted(rvas):
    print("\n=== %s  RVA 0x%X ===" % (k,rvas[k]))
    r=rvas[k]; seg=data[rva2off(r):rva2off(r)+0x120]
    n=0
    for ins in md.disasm(seg, IB+r):
        print("  %08X %-10s %s" % (ins.address, ins.mnemonic, ins.op_str)); n+=1
        if n>48: break