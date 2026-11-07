import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
def d(rva,n,tag):
    print("="*72); print("%s RVA %06X VA %08X"%(tag,rva,im.IB+rva))
    o=im.off(rva)
    if o is None: print("NO_RAW"); return
    for i in im.dis(rva,n): print("  %06X %s %s"%(i.address-im.IB,i.mnemonic,i.op_str))
d(0xAA580,0x80,"cmp eax,0x84 @0xAA5D8/0xAA5E3")
d(0x96FE8,0x120,"_CODOL_ReadClientCommand")
