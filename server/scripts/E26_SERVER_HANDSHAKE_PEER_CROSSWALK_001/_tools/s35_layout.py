import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
print("=== _CODOL_HandshakeInit 16-byte layout (0x9830A..0x98430) ===")
for i in im.dis(0x9830A,0x130): print("  %06X %s %s"%(i.address-im.IB,i.mnemonic,i.op_str))
