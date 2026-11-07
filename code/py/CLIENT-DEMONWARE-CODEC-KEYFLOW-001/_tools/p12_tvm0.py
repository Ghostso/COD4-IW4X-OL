import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
# control-flow from .text into .tvm0 (RVA 0xD958000..0xDC11000 => VA 0xDD58000..0xE011000)
tlo,thi=0xDD58000,0xE011000
refs=[]
for i in range(len(d)-5):
    if d[i] in (0xe8,0xe9):
        rel=struct.unpack_from("<i",d,i+1)[0]
        tgt=(IB+sva+i+5+rel)&0xffffffff
        if tlo<=tgt<thi: refs.append((IB+sva+i,d[i],tgt))
print("text->tvm0 rel32 refs:",len(refs))
for a,op,t in refs[:40]: print("  %08X op=%02X -> %08X"%(a,op,t))
# also indirect literals pointing into tvm0
pat_lo=struct.pack("<I",tlo)
print()
# constants search in .tvm0
tv=im.d[im.secs[5][3]:im.secs[5][3]+im.secs[5][4]]
for name,pat in [("CONST_A",bytes.fromhex("411309ae3fa3bcf31872eabc093211cc124254f4")),
                 ("CONST_B",bytes.fromhex("8022deaa0b1c21f400ffee37279210ceaaf43c21")),
                 ("PERM_A",bytes([7,0,0,0,17,0,0,0,14,0,0,0])),
                 ("LABEL_BDDATA",b"BDDATA"),("LABEL_CLIENTCHAL",b"CLIENTCHAL")]:
    print("tvm0 contains %-16s: %s"%(name, pat in tv))
print("tvm0 size",len(tv),"first32",tv[:32].hex(" "))
# entropy rough
import collections,math
c=collections.Counter(tv[:1<<20]); H=-sum(v/len(tv[:1<<20])*math.log2(v/len(tv[:1<<20])) for v in c.values())
print("tvm0 first1MB entropy %.3f bits/byte"%H)
