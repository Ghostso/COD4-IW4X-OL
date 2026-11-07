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
def scan_bytes(name,maxins=1200):
    s=syms[name]; rva=s["rva"]; off=pe.get_offset_from_rva(rva)
    code=d[off:off+maxins*8]
    ins_list=list(md.disasm(code,ib+rva))
    print("==== %s"%name)
    for i,ins in enumerate(ins_list):
        if ins.mnemonic=="call" and ins.op_str.startswith("0x") and "WriteByte" in nameat(int(ins.op_str,16)-ib):
            # look back for mov dword ptr [esp+4], imm
            for j in range(i-1,max(-1,i-4),-1):
                p=ins_list[j]
                if p.mnemonic=="mov" and "[esp + 4]" in p.op_str:
                    print("   %08x  WriteByte arg=%s   (call at %08x)"%(ins.address,p.op_str.split(",")[-1].strip(),ins.address)); break
    print()
for nm in ["_CODOL2697_WriteSnapshotReached","_CODOL2697_WriteGamestate"]:
    scan_bytes(nm)
