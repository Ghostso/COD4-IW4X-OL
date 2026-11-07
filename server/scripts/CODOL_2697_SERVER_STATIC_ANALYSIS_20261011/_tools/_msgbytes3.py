import json,io,sys,re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
paths={
 "NEW":r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe",
 "OLD":r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\codol_dedrun.exe",
 "1113":r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin\codol_dedrun.exe",
}
files={"NEW":"syms_NEW.json","OLD":"syms_OLD.json","1113":"syms_1113.json"}
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8")); m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
md=Cs(CS_ARCH_X86, CS_MODE_32)
immre=re.compile(r"^dword ptr \[esp \+ 4\], (0x[0-9a-f]+|\d+)$")
for tag in ["NEW","OLD","1113"]:
    syms=load(files[tag]); d=open(paths[tag],"rb").read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
    byrva={}
    for k,v in syms.items(): byrva.setdefault(v["rva"],k)
    print("############",tag)
    for name in ["_CODOL_WriteGamestate","_CODOL_WriteConfigstrings","_CODOL_WriteSnapshotDeltaNumber","_CODOL2697_WriteGamestate","_CODOL2697_WriteSnapshotReached","_SV_WriteReliableCommand"]:
        s=syms.get(name)
        if not s: print("  (absent) %s"%name); continue
        rva=s["rva"]; off=pe.get_offset_from_rva(rva); code=d[off:off+4000*8]
        ins=list(md.disasm(code,ib+rva))
        found=[]
        for i,insx in enumerate(ins):
            if insx.mnemonic=="call" and insx.op_str.startswith("0x"):
                tgt=int(insx.op_str,16)-ib
                if byrva.get(tgt,"")=="_CODOL_WriteByte":
                    v=None
                    for j in range(i-1,max(-1,i-4),-1):
                        m=immre.match(ins[j].op_str)
                        if m: v=int(m.group(1),0); break
                    found.append((insx.address-ib,v))
        print("  %-38s RVA=%08x"%(name,rva))
        print("      WriteByte sites: %s"%("; ".join("rva=%x val=%s"%(r,("0x%x"%v) if v is not None else "?") for r,v in found[:16])))
    print()
