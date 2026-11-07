import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for nm,tv in [("0x775A00",IB+0x775A00),("0x775A80",IB+0x775A80),("0x775AA4",IB+0x775AA4),("0x775AB0",IB+0x775AB0)]:
    print("%-10s callers: %s"%(nm,callers(tv)))
print()
# pointer-form refs across whole file
def ptrrefs(tva):
    pat=struct.pack("<I",tva); out=[]; i=0
    while True:
        j=img.d.find(pat,i)
        if j<0: break
        for nm,sva,svs,srp,srs,sx in img.secs:
            if srp<=j<srp+srs: out.append((nm,hex(sva+(j-srp)))); break
        i=j+1
    return out
for nm,tv in [("0x775A00",IB+0x775A00),("0x775AA4",IB+0x775AA4)]:
    print("%-10s ptr refs: %s"%(nm,ptrrefs(tv)))
