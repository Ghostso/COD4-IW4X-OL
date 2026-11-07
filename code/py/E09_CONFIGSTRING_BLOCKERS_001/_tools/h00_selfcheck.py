import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
for lbl,X,pairs in (("CLIENT",C,[(0x1AC1D0,0x1AB5D0),(0xA2E50,0xA2250)]),("SERVER",S,[(0xA0468,0x9F868),(0x99551,0x98951)])):
    print("== %s IB=0x%X ==" % (lbl,X.IB))
    for rva,exp in pairs:
        o,nm=X.off(rva)
        print("   RVA 0x%-7X -> off 0x%-7X section=%-8s expect=0x%-7X %s" % (rva,o,nm,exp,"OK" if o==exp else "MISMATCH"))