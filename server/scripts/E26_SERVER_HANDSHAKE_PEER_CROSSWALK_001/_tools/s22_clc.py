import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
print("=== clc jump table targets (0x473104/311B/3132/319A/2E6F) ===")
for rva in (0x473104,0x47311B,0x473132,0x47319A):
    print("--- RVA %06X ---"%rva)
    for i in im.dis(rva,0x14): print("   %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== _SV_UserMove head (0x725F1) ===")
for i in im.dis(0x725F1,0x60): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== _SV_ClientCommand (0x71701) head ===")
for i in im.dis(0x71701,0x50): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
