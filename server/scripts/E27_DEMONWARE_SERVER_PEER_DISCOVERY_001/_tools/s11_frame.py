import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
print("=== verify the s1x/reference 0x9CE310 framing site in the 2697 client ===")
for i in im.dis(0x9CE310-IB,0x50): print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("=== 2697 client: DEADBEEF read/compare context (0x686212) ===")
for i in im.dis(0x6861F0,0x40): print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
