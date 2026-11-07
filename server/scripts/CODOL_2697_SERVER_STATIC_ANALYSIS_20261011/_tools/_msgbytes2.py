import json,io,sys
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
for tag in ["NEW","OLD","1113"]:
    syms=load(files[tag]); d=open(paths[tag],"rb").read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
    byrva={}
    for k,v in syms.items(): byrva.setdefault(v["rva"],k)
    print("############",tag)
    for name in ["_CODOL_WriteGamestate","_CODOL_WriteConfigstrings","_CODOL_WriteSnapshotDeltaNumber","_CODOL2697_WriteGamestate","_CODOL2697_WriteSnapshotReached","_SV_WriteReliableCommand","_SV_ProfileCommand2697"]:
        s=syms.get(name)
        if not s: print("  (absent) %s"%name); continue
        rva=s["rva"]; off=pe.get_offset_from_rva(rva); code=d[off:off+3000*8]
        ins=list(md.disasm(code,ib+rva))
        found=[]
        for i,insx in enumerate(ins):
            if insx.mnemonic=="call" and insx.op_str.startswith("0x"):
                tgt=int(insx.op_str,16)-ib
                nm=byrva.get(tgt,"")
                if "WriteByte" in nm:
                    for j in range(i-1,max(-1,i-5),-1):
                        p=ins[j]
                        if p.mnemonic=="mov" and "[esp" in p.op_str and p.op_str.rstrip().endswith(tuple("0123456789abcdefx")):
                            found.append((hex(insx.address-ib),p.op_str.split(",")[-1].strip())); break
        print("  %-38s RVA=%08x  WriteByte(imm): %s"%(name,rva,"; ".join("%s=%s"%f for f in found[:14])))
    print()
