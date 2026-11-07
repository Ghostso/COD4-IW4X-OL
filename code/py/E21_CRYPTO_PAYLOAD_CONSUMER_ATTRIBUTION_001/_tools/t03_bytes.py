import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(P); d=C.d
print("imagebase",hex(C.IB))
for rva in (0x85b080,0x85b090,0x85b0a0,0x85b0a4,0x85b0c0,0x8bbc80,0x8bbd1c):
    o,nm=C.off(rva)
    if o is None: print(hex(rva),nm,None); continue
    b=d[o:o+64]
    print("RVA",hex(rva),"sec",nm,"off",hex(o),"hex",b.hex(),"ascii",repr(b))
def find_pat(pat,limit=20):
    out=[];i=0
    while True:
        j=d.find(pat,i)
        if j<0 or len(out)>=limit: break
        out.append(j); i=j+1
    return out
for pat in (b"HMAC calculation",b"HMAC mismatch",b"Bad recv counter",bytes.fromhex("7085aa00"),bytes.fromhex("90fe5800")):
    hits=find_pat(pat)
    print("PAT",pat,"hits",len(hits))
    for off in hits[:10]:
        # map file offset to RVA
        rv=None; sec=None
        for nm,va,vs,rp,rs in C.secs:
            if rp<=off<rp+rs: rv=va+(off-rp); sec=nm; break
        print("  off",hex(off),"rva",hex(rv) if rv is not None else None,sec)
