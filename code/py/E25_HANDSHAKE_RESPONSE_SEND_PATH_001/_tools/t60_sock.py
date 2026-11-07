import sys, pefile
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def d(va,n,tag):
    r=va-IB
    print("=== %s VA %08X RVA %06X sec=%s ==="%(tag,va,r,img.sec(r)))
    o=img.off(r)
    if o is None: print("  NO_RAW"); return
    for i in img.dis(r,n): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
d(0xB84950,0x50,"0xB84950 (socket holder setup, arg=?)")
d(0xB84B00,0x30,"0xB84B00 (close?)")
print()
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P)
want={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in e.imports:
        want[imp.address]=(e.dll.decode(),(imp.name or b'').decode(errors='replace'))
for a in (0xBAE4C8,0xBAE490,0xBAE4C4,0xBAE500,0xBAE4DC):
    print("  IAT %08X = %s"%(a,want.get(a)))
