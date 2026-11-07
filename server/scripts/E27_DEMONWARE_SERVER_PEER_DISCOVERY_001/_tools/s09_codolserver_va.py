import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# CODOLServer cited VAs: 0xBA1850 (0x85 sender), 0xBA0D20 (keyed-SHA1 helper), 0xBA3710 (recv verifier), 0xC73800 (SHA1 init), 0xBA0420 (2nd codec), 0xD5A4E0 (BDDATA str)
print("=== do CODOLServer-cited VAs resolve to code in the 2.6.9.7 recovered client? ===")
for va,label in [(0xBA1850,"0x85 sender"),(0xBA0D20,"keyed-SHA1 helper"),(0xBA3710,"recv verifier"),(0xC73800,"SHA1 init"),(0xBA0420,"2nd codec"),(0xBA02A0,"1st codec"),(0xD5A4E0,"BDDATA str")]:
    r=va-IB
    sec=im.sec(r) if 0<=r<0xDC14000 else None
    o=im.off(r) if sec else None
    first=None
    if o is not None:
        b=im.d[o:o+6]; first=b.hex()
    print("  VA %08X RVA %07X sec=%-8s raw_off=%s first6=%s"%(va,r,sec,hex(o) if o is not None else None,first))
