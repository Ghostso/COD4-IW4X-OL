import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_data\out_execmsg.txt","w",encoding="utf-8")
def d(rva,n,tag):
    OUT.write("="*76+"\n%s RVA %06X VA %08X\n"%(tag,rva,im.IB+rva))
    o=im.off(rva)
    if o is None: OUT.write("NO_RAW\n"); return
    for i in im.dis(rva,n): OUT.write("%06X %-22s %s %s\n"%(i.address-im.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
d(0x72DBB,0x400,"_SV_ExecuteClientMessage")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_data\out_execmsg.txt",encoding="utf-8").read())
