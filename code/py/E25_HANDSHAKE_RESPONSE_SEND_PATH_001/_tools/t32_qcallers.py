import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# function 0x6AA570 is the session ctor (ret 0x9c). Its callers:
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i]==0xe8:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of session-ctor 0x6AA570:", callers(IB+0x6AA570))
print()
# queue insert: the pump pops from +0xb8. Search callers of DF806F2
def callers_any(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i]==0xe8:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of enqueue 0xDF806F2 (VA):", callers_any(0xDF806F2))
print("callers of dequeue/consume 0x6A92A0:", callers_any(IB+0x6A92A0))
print("callers of 0x6A95A0:", callers_any(IB+0x6A95A0))
print("callers of 0x6AC4070:", callers_any(IB+0x6AC4070))
print()
# 0xDF806F2 is .tvm0; find refs to it as rel32 across .tvm0 too
tv=0xDF806F2
out=[]
for sec in img.secs:
    nm,sva,svs,srp,srs,sx=sec
    if srs==0: continue
    blob=img.d[srp:srp+srs]
    for i in range(len(blob)-5):
        if blob[i]==0xe8:
            rel=struct.unpack_from("<i",blob,i+1)[0]
            if ((IB+sva+i+5+rel)&0xffffffff)==tv: out.append((nm,hex(sva+i)))
print("enqueue 0xDF806F2 callers (all sections):",out)
