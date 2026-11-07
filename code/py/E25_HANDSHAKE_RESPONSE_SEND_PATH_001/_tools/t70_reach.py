import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def tgt(a):
    o=img.off(a)
    if img.d[o] not in (0xe8,0xe9): return None
    rel=struct.unpack_from("<i",img.d,o+1)[0]
    return (a+5+rel)&0xffffffff
print("=== walk call chain from 0x6AAA10 via any refs? try rel32 callers across .text ===")
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),data[i]))
    return out
print("callers of 0x6AAA10:", callers(IB+0x6AAA10))
print("callers of 0x6AAA320:", callers(IB+0x6AAA320))
print("callers of 0x6AAA570(ctor):", callers(IB+0x6AAA570))
print()
# maybe reached via vtable slot. search vtable ptr to 0x6AAA10/320/callers
def ptrrefs(tva):
    pat=struct.pack("<I",tva); out=[]; i=0
    while True:
        j=img.d.find(pat,i)
        if j<0: break
        for nm,sva,svs,srp,srs,sx in img.secs:
            if srp<=j<srp+srs: out.append((nm,hex(sva+(j-srp)))); break
        i=j+1
    return out
for tva,nm in [(IB+0x6AAA10,"0x6AAA10"),(IB+0x6AAA320,"0x6AAA320")]:
    print("ptr refs of %s: %s"%(nm,ptrrefs(tva)))
