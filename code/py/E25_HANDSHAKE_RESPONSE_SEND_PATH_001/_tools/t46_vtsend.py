import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def ref_all(va):
    pat=struct.pack("<I",va); out=[]; i=0
    while True:
        j=img.d.find(pat,i)
        if j<0: break
        # map file offset -> sec + rva
        m=None
        for nm,sva,svs,srp,srs,sx in img.secs:
            if srp<=j<srp+srs: m=(nm,sva+(j-srp)); break
        out.append((hex(j),m))
        i=j+1
    return out
for va,nm in [(0x775A00,"send-wrapper 0x775A00"),(0x775A22,"send-wrapper 0x775A22"),(0x775A50,"recv-wrapper 0x775A50"),(0x775A80,"sendto-wrapper 0x775A80")]:
    r=ref_all(va)
    print("%-24s VA %08X : %d 4-byte refs"%(nm,va,len(r)))
    for off,m in r[:12]: print("    fileoff %s sec/rva=%s"%(off,m))
print()
print("=== vtables 0xCC2550 / 0xCBBA5A4 seen at 0x41DDFA ===")
for va in (0xCC2550,0xCBBA5A4,0xCBBA4E8,0xCBBA56C):
    b=img.rd(va,0x30)
    print("  VA %08X sec=%s raw=%s"%(va,img.sec(va-IB), "yes" if b else "NO"))
    if b:
        for i in range(0,0x30,4):
            v=struct.unpack_from("<I",b,i)[0]
            print("     +%02X=%08X sec=%s"%(i,v,img.sec(v-IB) if 0x400000<=v<IB+img.pe.OPTIONAL_HEADER.SizeOfImage else None))
