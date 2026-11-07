import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
from capstone import *
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
data=im.d[rp:rp+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32)
targets=[0x5D0,0x5D4,0x5E0,0x5E8,0x5EC,0x5F0,0x5F4,0x5F8,0x5FC,0x600,0x604,0x608,0x60C,0x610,0x614,0x618,0x61C,0x620,0x624,0x628]
def refs(disp):
    pat=struct.pack("<I",disp); out=[]
    i=data.find(pat)
    while i!=-1:
        # candidate instruction start: try starts i-9..i-5, require exact decode ending at i+4 and bracketed disp
        ok=None
        for st in range(max(0,i-9), i-4):
            for ins in md.disasm(data[st:i+4+8], IB+sva+st, count=2):
                if ins.address+len(ins.bytes)==IB+sva+i+4 and ("0x%x"%disp) in ins.op_str and "[" in ins.op_str:
                    ok=(IB+sva+st, ins.mnemonic, ins.op_str); break
                if ins.address+len(ins.bytes)>IB+sva+i+4: break
            if ok: break
        if ok: out.append(ok)
        i=data.find(pat,i+1)
    return out
for t in targets:
    r=refs(t)
    print("== obj+%03X  instr refs=%d"%(t,len(r)))
    for a,mn,ops in r:
        tag = "WRITE" if (ops.startswith("mov dword ptr") or ops.startswith("mov byte ptr") or ops.startswith("mov word ptr")) else "read"
        print("    %08X %-26s %s %s"%(a,mn+" "+ops,tag,""))
