import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.tvm0'][0]
tv=im.d[rp:rp+rs]
print("tvm0 VA %08X VS %08X raw %08X"%(im.IB+sva,vs,rs))
for off in (0x5F0,0x5F4,0x5F8,0x5F9,0x5FC,0x60C,0x60D):
    pat=struct.pack("<I",off)
    c=tv.count(pat)
    idx=[]; i=tv.find(pat)
    while i!=-1 and len(idx)<6:
        idx.append(im.IB+sva+i); i=tv.find(pat,i+1)
    print("  dword %08X count=%d %s"%(off,c,[hex(a) for a in idx]))
print()
print("codec CONST tables in tvm0:")
for nm,pat in [("A_20const",bytes.fromhex("411309ae3fa3bcf31872eabc093211cc124254f4")),
               ("B_20const",bytes.fromhex("8022deaa0b1c21f400ffee37279210ceaaf43c21")),
               ("AE09",bytes.fromhex("411309ae")),("AADE",bytes.fromhex("8022deaa"))]:
    print("   %-10s %s"%(nm, tv.count(pat)))
# unique targets of text->tvm0 rel32
d=im.d; nt,st,vt2,rpt,rst,xt=[s for s in im.secs if s[0]=='.text'][0]
td=d[rpt:rpt+rst]
tlo,thi=im.IB+sva, im.IB+sva+vs
from collections import Counter
c=Counter()
for i in range(len(td)-5):
    if td[i] in (0xe8,0xe9):
        rel=struct.unpack_from("<i",td,i+1)[0]
        tgt=(im.IB+st+i+5+rel)&0xffffffff
        if tlo<=tgt<thi: c[tgt]+=1
print("distinct tvm0 entry targets:",len(c))
for t,k in c.most_common(12): print("   %08X x%d"%(t,k))
