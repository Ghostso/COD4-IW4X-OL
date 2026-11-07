import sys, re
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
for lbl,X in (("CLIENT-Rec",C),("SERVER",S)):
    print("=== %s: configstring-related ASCII tokens ===" % lbl)
    for tok in (b"configstring",b"CS_",b"configstrings",b"ConfigString"):
        c=X.d.count(tok)
        if c: print("   %-14r count=%d" % (tok,c))
print()
print("NOTE: token presence is NOT proof of reader identity (E-06 F-05 lesson).")