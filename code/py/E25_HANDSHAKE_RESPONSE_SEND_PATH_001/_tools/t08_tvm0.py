import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_tvm0_queue.txt","w",encoding="utf-8")
def d(va,n,tag):
    OUT.write("="*76+"\n%s VA %08X RVA %06X sec=%s\n"%(tag,va,va-IB,img.sec(va-IB)))
    o=img.off(va-IB)
    if o is None: OUT.write("NO_RAW\n"); return
    for i in img.dis(va-IB,n):
        OUT.write("%06X %-20s %s %s\n"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
d(0xDF806F2,0x80,"VA 0xDF806F2 (enqueue from 6AA230)")
d(0xDF37227,0x50,"VA 0xDF37227 (release)")
d(0xDF9AA45,0x40,"VA 0xDF9AA45 (alloc)")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_tvm0_queue.txt",encoding="utf-8").read())
