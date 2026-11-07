import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C)
print("=== CLIENT RVA 0x9BF80..0x9C040 (challengeResponse ref @0x9BFB9) ===")
for i in im.dis(0x9BF80,0xC0): print("  %06X %-20s %s %s"%(i.address-im.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
