import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def ins_range(rva, n):
    return list(img.dis(rva,n))
def calls_in(rva,n,only_imm=True):
    out=[]
    for i in ins_range(rva,n):
        if i.mnemonic in ("call","jmp"):
            if i.operands and i.operands[0].type==1:
                t=(i.operands[0].imm)&0xffffffff
                out.append((i.address-IB,i.mnemonic,t,img.sec(t-IB) if 0x1000<=t-IB<0x800000 else None))
            else:
                out.append((i.address-IB,i.mnemonic,i.op_str,None))
    return out
print("=== indirect/register calls in 0x6AA7B0 (pump) ===")
for site,mn,op,sec in calls_in(0x6AA7B0,0x130):
    if sec is None or mn=="call":
        print("  %06X %-4s %s  sec=%s"%(site,mn,op,sec))
print()
print("=== call/jmp in 0x6AA230 ===")
for site,mn,op,sec in calls_in(0x6AA230,0x100):
    print("  %06X %-4s %s  sec=%s"%(site,mn,op,sec))
