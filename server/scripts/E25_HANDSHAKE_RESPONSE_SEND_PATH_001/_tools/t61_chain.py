import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# capture the whole chain dumps for the record
out=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_chain.txt","w",encoding="utf-8")
def d(rva,n,tag):
    out.write("="*76+"\n%s RVA %06X VA %08X sec=%s\n"%(tag,rva,IB+rva,img.sec(rva)))
    o=img.off(rva)
    if o is None: out.write("NO_RAW\n"); return
    for i in img.dis(rva,n): out.write("%06X %-20s %s %s\n"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
d(0x6ABAA0,0x70,"A: caller block 0x6ABAA0 (data0=data1)")
d(0x6AA230,0x100,"B: 0x6AA230 enqueue")
d(0x320E30,0x60,"C: 0x320E30 node clone")
d(0x6AA7B0,0xC0,"D: 0x6AA7B0 pump")
d(0x783B50,0x20,"E: 0x783B50 send-fd wrapper")
d(0x784E40,0x50,"F: 0x784E40 -> ws2_32!send")
d(0x784950,0x50,"G: 0x784950 socket setup")
d(0x784B00,0x30,"H: 0x784B00 closesocket")
out.close()
print("wrote chain dump; lines:",sum(1 for _ in open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_chain.txt",encoding="utf-8")))
