import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# client: read opcode at 6AC178 branch on [esi+0x5CC] (1,2,3) and msgcode 0x81/0x04/0x83/0x84/0x85
print("=== client msgcode/opcode constants (from E-24/E-25) ===")
for rva,lab in [(0x6AC186,"cmp al,0x81"),(0x6AC19C,"cmp al,0x04"),(0x6AC1CA,"cmp al,0x83"),(0x6AC240,"cmp al,0x84"),(0x6AC2DC,"cmp al,0x85"),(0x6AC300,"cmp al,0x84")]:
    o=im.off(rva); b=im.d[o:o+6]
    print("  RVA %06X %-14s bytes=%s"%(rva,lab,b.hex()))
print()
# client phase writes
print("=== client [+0x5CC] writes ===")
for rva,val in [(0x6AA46E,1),(0x6ABB01,2),(0x6AB2ED,3),(0x6A1310,0),(0x6A13F0,0)]:
    o=im.off(rva); b=im.d[o:o+10]
    print("  RVA %06X bytes=%s"%(rva,b.hex()))
