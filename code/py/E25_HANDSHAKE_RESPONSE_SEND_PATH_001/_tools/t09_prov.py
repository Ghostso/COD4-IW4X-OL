import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== all writes to esi / ebx within 0x6AB310..0x6ABB8E ===")
for i in img.dis(0x6AB310, 0x6ABB8E-0x6AB310):
    s=i.op_str; m=i.mnemonic
    dst=s.split(",")[0].strip()
    if m=="mov" and dst in ("esi","ebx","edi","ebp"):
        print("  %06X %-22s %s %s"%(i.address-IB,bytes(i.bytes).hex(),m,s))
    if m=="xor" and dst in ("esi","ebx"): print("  %06X %-22s %s %s"%(i.address-IB,bytes(i.bytes).hex(),m,s))
    if m=="lea" and dst in ("esi","ebx"): print("  %06X %-22s %s %s"%(i.address-IB,bytes(i.bytes).hex(),m,s))
    if m=="call" and "eax" in s and False: pass
print()
print("=== resolved call targets in 0x6AB310 (call sites + targets) ===")
for i in img.dis(0x6AB310, 0x6ABB8E-0x6AB310):
    if i.mnemonic=="call" and i.operands and i.operands[0].type==1:
        t=i.operands[0].imm & 0xffffffff
        print("  %06X -> VA %08X RVA %06X sec=%s"%(i.address-IB,t,t-IB,img.sec(t-IB)))
