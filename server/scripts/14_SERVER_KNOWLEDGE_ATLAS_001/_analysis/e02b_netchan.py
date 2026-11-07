import json, pefile, struct
from capstone import *
sym=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding="utf-8"))
want=["_CODOL_NetchanProcess","_CODOL_NetchanSubmit","_CODOL_NetchanTransmit","_CODOL_NetchanTransmitNextFragment","_Netchan_Transmit","_Netchan_Process"]
rvas={}
for s in sym["symbols"]:
    if s["name"] in want and s.get("section")==".text": rvas[s["name"]]=int(s["rva"])
print("=== 2697 server: CODOL netchan symbols ===")
for k in want: print("  %-34s %s" % (k, ("RVA 0x%X"%rvas[k]) if k in rvas else "ABSENT"))
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86, CS_MODE_32)
for k in ["_CODOL_NetchanTransmitNextFragment","_CODOL_NetchanTransmit"]:
    if k not in rvas: continue
    r=rvas[k]; o=rva2off(r)
    print("\n=== disasm %s (RVA 0x%X) first 40 insns ===" % (k,r))
    n=0
    for ins in md.disasm(data[o:o+0x180], IB+r):
        print("   %08X %-10s %s" % (ins.address, ins.mnemonic, ins.op_str)); n+=1
        if n>=40: break