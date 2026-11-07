import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
# jump table entries are VAs -> RVA = VA-0x400000
print("=== clc jump table (VA -> RVA) ===")
for k in range(5):
    v=im.u32(0x7B37A0+k*4-IB)
    print("  clc[%d] VA %08X -> RVA %06X"%(k,v,v-IB))
print()
for rva in (0x73104,0x7311B,0x73132,0x7319A):
    print("--- RVA %06X ---"%rva)
    for i in im.dis(rva,0x16): print("   %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
