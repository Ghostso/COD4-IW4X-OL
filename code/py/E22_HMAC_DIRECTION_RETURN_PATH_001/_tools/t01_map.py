import sys,struct,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[]
for s in pe.sections:
    name=s.Name.rstrip(b"\0").decode(errors="replace")
    va=s.VirtualAddress; vs=s.Misc_VirtualSize; raw=s.PointerToRawData; rs=s.SizeOfRawData; ch=s.Characteristics
    secs.append((name,va,vs,raw,rs,ch))
def sec_of(rva):
    for x in secs:
        n,va,vs,raw,rs,ch=x
        if va<=rva<va+vs: return x
    return None
def off(rva):
    x=sec_of(rva)
    if not x: return None
    n,va,vs,raw,rs,ch=x
    if rs==0 or rva-va>=rs: return None
    return raw+(rva-va)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(a,b,tag):
    print("="*78); print(tag,hex(a),hex(b)); print("-"*78)
    o=off(a)
    if o is None: print("NO_FILE_BYTES section",sec_of(a)); return
    for ins in md.disasm(d[o:o+(b-a)],IB+a):
        print("%06X %-24s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
print("SECTIONS")
for x in secs:
    n,va,vs,raw,rs,ch=x
    print("%-8s VA=%08X VS=%08X RAW=%08X RS=%08X CH=%08X exec=%s"%(n,va,vs,raw,rs,ch,bool(ch&0x20000000)))
for rva in (0x6AAE70,0x6AC0C0,0xA85AD0,0xAAB260,0xAAB310,0xAAB1C0,0xA87830,0xDF4A028):
    x=sec_of(rva); o=off(rva)
    print("ADDR",hex(rva),"sec",x[0] if x else None,"raw_off",hex(o) if o is not None else None,"exec",bool(x[5]&0x20000000) if x else None)
# full disasm
show(0x6AAE70,0x6AB180,"0x6AAE70 full")
show(0x6AC0C0,0x6AC3D0,"0x6AC0C0 full")
# find direct calls inside 0x6AC0C0 and 0x6AAE70
def find_calls(func,start,end,target):
    o=off(start)
    if o is None:return
    for ins in md.disasm(d[o:o+(end-start)],IB+start):
        if ins.mnemonic=="call":
            for op in ins.operands:
                if op.type==1 and (op.imm&0xffffffff)==(IB+target)&0xffffffff:
                    print("CALL_TARGET",hex(ins.address-IB),"->",hex(target),"bytes",bytes(ins.bytes).hex())
for t in (0x6AAE70,0xA85AD0,0xAAB260,0xAAB310):
    print("SEARCH CALL in 6AC0C0 ->",hex(t)); find_calls(0,0x6AC0C0,0x6AC3D0,t)
