import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# client: find the 3-bit clc reader: bytes "6a 03" then call MSG_ReadBits-like, then cmp reg,4 then jmp table
# search for pattern: push 3 ; ... ; cmp <reg>,4 ; ja ; jmp [reg*4+disp]
o=im.off(0x1000); blob=im.d[o:o+0x7ACA00]
for i in range(len(blob)-40):
    if blob[i]==0x6a and blob[i+1]==0x03:
        seg=blob[i:i+60]
        # look for 'ff 24' jmp table within 60 bytes
        j=seg.find(b"\xff\x24")
        if j>=0:
            rva=0x1000+i
            if 0x600000<=rva<=0x700000:
                print("push 3 @client %06X  ...%s"%(rva, seg[max(0,j-14):j+8].hex()))
