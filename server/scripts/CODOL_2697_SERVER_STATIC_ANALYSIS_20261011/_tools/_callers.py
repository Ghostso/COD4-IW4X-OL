import json,io,sys
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
tbody=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
tbase=ib+text.VirtualAddress
# build sorted list of function starts (only code, section .text)
funcs=sorted([(v["rva"],k) for k,v in syms.items() if v["section"]==".text"])
import bisect
starts=[f[0] for f in funcs]
def owner(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    return funcs[i][1]
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva): return byrva.get(rva,"")
def callers(target_name):
    t=syms.get(target_name)
    if not t: return []
    trva=t["rva"]; res=[]
    for ins in md.disasm(tbody,tbase):
        if ins.mnemonic=="call" and ins.op_str.startswith("0x"):
            if int(ins.op_str,16)-ib==trva:
                r=ins.address-ib
                res.append((r,owner(r)))
    return res
for t in ["_CODOL2697_WriteSnapshot","_CODOL2697_WriteSnapshotReached","_CODOL2697_WriteGamestate","_CODOL2697_WriteConfigstrings","_CODOL2697_WriteDeltaValue","_CODOL2697_ReadRegistration"]:
    print("CALLERS of",t)
    for r,o in callers(t): print("   %#010x  in %s"%(r,o))
    print()
