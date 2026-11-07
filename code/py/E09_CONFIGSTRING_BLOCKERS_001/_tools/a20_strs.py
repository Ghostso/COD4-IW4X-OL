import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for va in (0xCC0CB4,0xCC0CD4,0xCB8344,0xCB8354):
    b=C.bytes_rva(va-C.IB,96)
    print("VA 0x%X : %r" % (va,(b.split(b'\0')[0] if b else None)))