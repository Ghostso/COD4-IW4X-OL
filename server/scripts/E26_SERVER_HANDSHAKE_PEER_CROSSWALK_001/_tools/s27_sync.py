import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
print("=== _SV_Netchan_Decode re-sync at 0x855C0 ===")
for i in im.dis(0x855E0,0x90): print("  %06X %-20s %s %s"%(i.address-im.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
