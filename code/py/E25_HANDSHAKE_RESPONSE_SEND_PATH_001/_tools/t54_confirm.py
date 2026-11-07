import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== 0x783B50 (send) and 0x783B70 (recv) side by side ===")
for i in img.dis(0x783B50,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
# confirm IAT targets by pefile
import pefile
pe=pefile.PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for e in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in e.imports:
        if imp.address in (0xBAE4C8,0xBAE490,0xBAE504,0xBAE50C,0xBAE4DC):
            print("  IAT %08X = %s!%s"%(imp.address,e.dll.decode(),(imp.name or b'').decode()))
print()
print("=== 0x6A97E0 pair fields recap ===")
for i in img.dis(0x6A97E9,0x30): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0x589230 / 0xB7FD10 / 0xAC4070 accessors ===")
for rva in (0x589230,0x77FD10,0x6C4070):
    for i in img.dis(rva,8): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
