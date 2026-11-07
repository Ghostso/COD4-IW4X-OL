import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
for lo,hi,tag in [(0x985F0,0x98680,"HandshakeCookie @0x98610"),(0x165E20,0x165E70,"cmp al,0x84 @0x165E38"),(0x3416E0,0x341720,"cmp al,0x84 @0x3416FF")]:
    print("="*70); print(tag)
    for i in im.dis(lo,hi-lo): print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
