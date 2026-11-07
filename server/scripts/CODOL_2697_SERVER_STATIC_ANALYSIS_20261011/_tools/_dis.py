import json,io,sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8"))
    m={}
    for s in d["symbols"]:
        m.setdefault(s["name"],s)
    return m
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
syms=load("syms_NEW.json")
d=open(NEW,"rb").read()
pe=pefile.PE(data=d, fast_load=True)
ib=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86, CS_MODE_32)
# name lookup by rva
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva):
    return byrva.get(rva,"")
def disasm(name, maxins=400):
    s=syms.get(name)
    if not s: print("NO SYM",name); return
    rva=s["rva"]; off=pe.get_offset_from_rva(rva)
    code=d[off:off+maxins*8]
    print("==== %s  rva=%#x va=%#x"%(name,rva,ib+rva))
    n=0
    for ins in md.disasm(code, ib+rva):
        cm=""
        if ins.mnemonic.startswith("call") or ins.mnemonic.startswith("jmp"):
            m=ins.op_str
            if m.startswith("0x"):
                t=int(m,16)-ib
                nm=nameat(t)
                if nm: cm="  ; -> %s"%nm
        print("  %08x  %-8s %s%s"%(ins.address,ins.mnemonic,ins.op_str,cm))
        n+=1
        if n>=maxins: break
        if ins.mnemonic=="ret": break
    print()
for nm in ["_SV_SendMessageToClient"]:
    disasm(nm,600)
