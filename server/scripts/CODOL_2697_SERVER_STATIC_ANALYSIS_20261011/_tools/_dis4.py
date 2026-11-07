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
byrva={}
for k,v in syms.items(): byrva.setdefault(v["rva"],k)
def nameat(rva): return byrva.get(rva,"")
def callers(t):
    s=syms.get(t)
    if not s: return []
    tr=s["rva"]; res=[]
    for ins in md.disasm(tbody,tbase):
        if ins.mnemonic=="call" and ins.op_str.startswith("0x") and int(ins.op_str,16)-ib==tr:
            r=ins.address-ib; res.append((r,owner(r)))
    return res
for t in ["_CODOL_WriteServerGamestate","_CODOL_WriteServerSnapshot","_CODOL_WriteByte","_CODOL2697_WriteGamestate"]:
    print("CALLERS of",t)
    for r,o in callers(t): print("   %#010x  in %s"%(r,o))
    print()
# dump _CODOL_WriteServerGamestate and _CODOL2697_WriteGamestate head
def dump(name,maxins):
    s=syms.get(name)
    if not s: print("NO",name); return
    rva=s["rva"]; off=pe.get_offset_from_rva(rva); code=d[off:off+maxins*8]
    print("==== %s rva=%#x"%(name,rva)); n=0
    for ins in md.disasm(code,ib+rva):
        cm=""
        if ins.mnemonic.startswith(("call","jmp")) and ins.op_str.startswith("0x"):
            nm=nameat(int(ins.op_str,16)-ib)
            if nm: cm="  ; -> %s"%nm
        print("  %08x  %-8s %s%s"%(ins.address,ins.mnemonic,ins.op_str,cm)); n+=1
        if n>=maxins: break
    print()
dump("_CODOL_WriteServerGamestate",80)
dump("_CODOL_WriteServerSnapshot",70)
