import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
o=im.off(0x1000); blob=im.d[o:o+0x382BF8]
print("=== immediate compares (3C/3D/80/81/83) to 0x81/0x83/0x84/0x85 ===")
for op in (0x81,0x83,0x84,0x85):
    al=[0x1000+i for i in range(len(blob)-2) if blob[i]==0x3c and blob[i+1]==op]           # cmp al,imm8
    eax=[0x1000+i for i in range(len(blob)-5) if blob[i]==0x3d and struct.unpack_from('<I',blob,i+1)[0]==op]  # cmp eax,imm32
    rm=[0x1000+i for i in range(len(blob)-7) if blob[i:2+i]==b"\x81" and blob[i+2] in (0xf8,0xf9,0xfa,0xfb,0xfd) and struct.unpack_from('<I',blob,i+3)[0]==op]
    print("  %02X : cmp al=%s  cmp eax=%s  cmp r/m32=%s"%(op,[hex(x) for x in al],[hex(x) for x in eax],[hex(x) for x in rm]))
