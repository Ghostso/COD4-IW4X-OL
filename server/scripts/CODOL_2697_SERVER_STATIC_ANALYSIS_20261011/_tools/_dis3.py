import json,io,sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8"))
    m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
syms=load("syms_NEW.json")
d=open(NEW,"rb").read()
pe=pefile.PE(data=d, fast_load=True)
ib=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86, CS_MODE_32)
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva): return byrva.get(rva,"")
def dump(name, maxins, out):
    s=syms.get(name)
    if not s: out.write("NO SYM "+name+"\n"); return
    rva=s["rva"]; off=pe.get_offset_from_rva(rva)
    code=d[off:off+maxins*8]
    out.write("==== %s  rva=%#x va=%#x\n"%(name,rva,ib+rva))
    n=0
    for ins in md.disasm(code, ib+rva):
        cm=""
        if ins.mnemonic.startswith(("call","jmp")):
            m=ins.op_str
            if m.startswith("0x"):
                nm=nameat(int(m,16)-ib)
                if nm: cm="  ; -> %s"%nm
        out.write("  %08x  %-8s %s%s\n"%(ins.address,ins.mnemonic,ins.op_str,cm)); n+=1
        if n>=maxins: break
        if ins.mnemonic=="ret" and ins.address==ib+rva: 
            pass
    out.write("\n")
targets=[("_CODOL_WriteGamestate",120),("_CODOL2697_WriteGamestate",900),
         ("_CODOL_WriteSnapshot",60),("_CODOL2697_WriteSnapshot",900),
         ("_CODOL_WriteConfigstrings",60),("_CODOL2697_WriteConfigstrings",500),
         ("_CODOL2697_ReadRegistration",400),("_CODOL2697_WriteNativeGamestate",300),
         ("_CODOL2697_ProfileCommandBytes",200)]
with open(base+r"\disasm_key2697.txt","w",encoding="utf-8") as f:
    for nm,mx in targets: dump(nm,mx,f)
print("written", base+r"\disasm_key2697.txt")
