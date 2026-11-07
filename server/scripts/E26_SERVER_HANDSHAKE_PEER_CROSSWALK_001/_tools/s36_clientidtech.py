import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# client: look for 3-bit clc read (call with '3') near a 0..4 jump table; search for the 0..4 table pattern
print("=== client: any 'push 3' + indirect jmp [reg*4+table] with 5 entries? ===")
found=0
o=im.off(0x1000); blob=im.d[o:o+0x7ACA00]
for i in range(len(blob)-8):
    # ff 24 85/8d/95/bd disp32  => jmp [reg*4+disp32]
    if blob[i]==0xff and blob[i+1] in (0x24,) and blob[i+2] in (0x85,0x8d,0x95,0x9d,0xa5,0xad,0xb5,0xbd):
        disp=struct.unpack_from('<I',blob,i+3)[0]
        if 0x400000<=disp<0xDC14000:
            rva=0x1000+i
            if 0x690000<=rva<=0x6D0000:
                print("   jmp table client RVA %06X -> table VA %08X"%(rva,disp))
                if found<6: found+=1
print("done, candidates:",found)
print()
# client Demonware descriptors known from earlier rounds
for kw in [b"bdCore",b"BDCore",b"Demonware",b"demonware",b"bds",b"BD_SESSION",b"dwSession"]:
    print("client %-12s %d"%(kw.decode(),im.d.count(kw)))
