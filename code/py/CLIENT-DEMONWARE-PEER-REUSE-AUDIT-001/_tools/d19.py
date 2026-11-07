import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
def cstr(va,n=64):
    b=im.rd(va,n)
    return b.split(b"\x00")[0] if b else None
print("0xC4461C ->", cstr(0xC4461C))
print()
print("crypto method table @0xD49B28 (0x68-byte entries):")
for k in range(12):
    ent=0xD49B28+0x68*k
    p=im.u32(ent)
    s=cstr(p,64) if p else None
    print("  [%2d] VA %08X name_ptr %08X %r"%(k,ent,p,s))
