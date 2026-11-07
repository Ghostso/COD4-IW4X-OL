import sys,struct,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[]
for s in pe.sections:
    secs.append((s.Name.rstrip(b"\0").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))
def sec(rva):
    for n,va,vs,rp,rs in secs:
        if va<=rva<va+vs:return (n,va,vs,rp,rs)
def off(rva):
    x=sec(rva)
    if not x:return None
    n,va,vs,rp,rs=x
    if rs==0 or rva-va>=rs:return None
    return rp+rva-va
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(a,b,tag):
 print("="*70);print(tag,hex(a),hex(b));
 o=off(a)
 if o is None:print("NO_RAW",sec(a));return
 for ins in md.disasm(d[o:o+b-a],IB+a):print("%06X %-20s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
# Verify call target instruction encoding in 6AC2F0: e8 7b eb ff ff -> target?
for ins_addr,rel in [(0x6AC2F0,0xffffeb7b-0x100000000),(0x6AC2BC,0xffff991f-0x100000000),(0x6AC37B,0xffff9860-0x100000000)]:
 print("relcalc",hex(ins_addr),"rel",rel,"target",hex((IB+ins_addr+5+rel)&0xffffffff),"rva",hex((ins_addr+5+rel)&0xffffffff))
# show around code calls
show(0x6AC280,0x6AC340,"call context")
# Check 0xA87830 / 0xA878A0 mapping
for a in (0xA87830,0xA878A0,0xA85AD0,0xA85BE0,0xA85640,0x6A8BF0,0x6AAE70):
 print("MAP",hex(a),sec(a),"off",off(a))
