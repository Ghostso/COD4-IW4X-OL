import struct, sys
DUMP = r"D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
d = open(DUMP,"rb").read(); BASE=0x400000
def table(a,n): 
    o=a-BASE; return [struct.unpack_from("<Iii",d,o+i*12) for i in range(n)]
PS=table(0xDA8078,0x57)

class R:
    def __init__(s,data,pos=0): s.d=data; s.c=pos; s.b=pos*8; s.o=False
    def bit(s):
        if (s.b&7)==0:
            if s.c>=len(s.d): s.o=True; return 0
            s.b=s.c*8; s.c+=1
        v=(s.d[s.b>>3]>>(s.b&7))&1; s.b+=1; return v
    def bits(s,n):
        v=0
        for i in range(n): v|=s.bit()<<i
        return v
    def raw(s,n):
        b=s.d[s.c:s.c+n]; s.c+=n; return b

def run(s,w):
    if w==1:
        n=0
        while s.bit(): n+=1
        return n
    if s.bit(): return 1
    m=(1<<w)-1; n=1
    while True:
        v=s.bits(w); n+=v
        if v!=m: return n

def fld(s,idx,base,absolute=False):
    off,bits,_=PS[idx]
    if bits==0:
        if s.bit()==0: return s.bit()<<31
        if s.bit()==1: return s.bits(32)^base
        return ("c",s.bits(5),s.bits(5))
    if s.bit()==0: return 0 if absolute else base
    return s.bits(bits)^(0 if absolute else base)

def dec(data,totalw=7,runw=1,verbose=False):
    s=R(data)
    s.raw(4); s.raw(1); s.raw(4); s.raw(1); s.raw(1)
    s.bit(); s.bit(); s.bits(8)
    v=[0]*len(PS)
    if s.bit()==0:
        for i in range(len(PS)): v[i]=fld(s,i,0,True)
        return v,"FULL",s
    total=s.bits(totalw)
    if verbose: print("total =",total)
    if total>len(PS): s.o=True; return v,"TOTAL_OVF",s
    last=-1; g=0
    while True:
        g+=1
        if g>300: s.o=True; return v,"LOOP",s
        idx=last+run(s,runw)
        if verbose: print("  next idx",idx)
        for i in range(last+1,idx):
            if i>=len(PS): s.o=True; return v,"OVF",s
            v[i]=fld(s,i,0,True)
        if idx>=len(PS): s.o=True; return v,"OVF",s
        v[idx]=fld(s,idx,0,True)
        last=idx
        if idx==total: break
    return v,"DELTA",s

h=open(sys.argv[1]).read().strip(); data=bytes.fromhex(h)
for tw,rw in [(7,1),(7,7),(7,3)]:
    v,k,s=dec(data,tw,rw,False)
    print("totalw=%d runw=%d -> %-10s ovf=%s bits=%d bytes=%d"%(tw,rw,k,s.o,s.b,(s.b+7)//8))
print()
v,k,s=dec(data,7,1,True)
print("kind",k,"ovf",s.o,"bits",s.b,"bytes",(s.b+7)//8,"of",len(data))