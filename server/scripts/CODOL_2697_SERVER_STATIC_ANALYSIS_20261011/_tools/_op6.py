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
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva): return byrva.get(rva,"")
def win(va,lo,hi):
    off=pe.get_offset_from_rva(va-ib); code=d[off:off+900*8]
    for ins in md.disasm(code,ib+va):
        if ins.address> hi: break
        if ins.address<lo: continue
        cm=""
        if ins.mnemonic.startswith(("call","jmp")) and ins.op_str.startswith("0x"):
            nm=nameat(int(ins.op_str,16)-ib)
            if nm: cm="  ; -> %s"%nm
        print("  %08x  %-8s %s%s"%(ins.address,ins.mnemonic,ins.op_str,cm))
print("### _CODOL2697_WriteGamestate around 0x4a21b8..0x4a2330")
win(0x4a21b8,0x4a21b8,0x4a2340)
print()
print("### _CODOL2697_WriteSnapshotReached around 0x4a4c40..0x4a4d10")
win(0x4a4860,0x4a4c40,0x4a4d10)
