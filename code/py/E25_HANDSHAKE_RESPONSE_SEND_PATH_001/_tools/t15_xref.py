import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def xref(func_rva, nbytes, tag):
    print("="*78); print(tag, "RVA %06X VA %08X"%(func_rva, IB+func_rva))
    o=img.off(func_rva)
    calls=[]
    for i in img.dis(func_rva, nbytes):
        if i.mnemonic in ("call","jmp") and i.operands and i.operands[0].type==1:
            tva=i.operands[0].imm & 0xffffffff
            trva=tva-IB
            calls.append((i.address-IB, trva, img.sec(trva) if 0x400000<=tva<0x100000000 else None))
    for site,trva,sec in calls:
        print("  %06X -> RVA %06X sec=%s" % (site, trva, sec))
    return calls
xref(0x6AA230, 0x100, "0x6AA230")
xref(0x6AA7B0, 0x1C0, "0x6AA7B0")
xref(0x6AB310, 0x880, "0x6AB310")
