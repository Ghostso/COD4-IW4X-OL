import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(P)
# .text bounds
text=[s for s in C.secs if s[0]==".text"][0]
_,tva,tvs,trp,trs=text
data=C.d[trp:trp+trs]
def find(val):
    # search exact little-endian VA and call/jmp rel32 operands
    va=(C.IB+val)&0xffffffff
    pat=struct.pack("<I",va)
    hits=[]
    i=0
    while True:
        j=data.find(pat,i)
        if j<0: break
        hits.append(tva+j)
        i=j+1
    return hits
def find_calls(target):
    tv=(C.IB+target)&0xffffffff
    hits=[]
    for i in range(len(data)-5):
        if data[i] in (0xE8,0xE9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            dst=(C.IB+tva+i+5+rel)&0xffffffff
            if dst==tv: hits.append((tva+i,hex(data[i])))
    return hits
for name,val in [("HMAC mismatch",0x85b0ec),("HMAC calculation",0x85b0fc),("Bad recv counter",0x85b110),("Bad frame/payload size",0x85b124),("vtable 0x85B0A4",0x85b0a4),("vtable 0x85B0E0",0x85b0e0),("vtable 0x8BBD1C",0x8bbd1c)]:
    print("REF",name,hex(val),[hex(x) for x in find(val)])
for name,t in [("ctor 0x6A84E0",0x6a84e0),("second 0x6A9720",0x6a9720),("handler 0x6A9920",0x6a9920)]:
    print("CALLREFS",name,[hex(a)+":"+op for a,op in find_calls(t)][:200],"count",len(find_calls(t)))
