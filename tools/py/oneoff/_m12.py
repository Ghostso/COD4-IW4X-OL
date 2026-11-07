import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
BASE=0x400000; END=BASE+0x0E659000
def find_rel_call(target, lo=BASE, hi=END):
    out=[]; i=BASE-LO
    buf=data[BASE-LO:END-LO]
    # E8 rel32 where next_insn+rel == target
    k=0
    while True:
        k=buf.find(b"\xE8",k)
        if k<0: break
        if k+5<=len(buf):
            rel=struct.unpack_from("<i",buf,k+1)[0]
            a=BASE+k
            if a+5+rel==target: out.append(a)
        k+=1
    return out
for t in (0x00BA4430,0x00BA41D0,0x00B765A0,0x00B9BBB0,0x00B779A0):
    xs=find_rel_call(t)
    print("0x%08X  direct call xrefs = %d  %s"%(t,len(xs),", ".join("0x%X"%x for x in xs[:8])))
# also count vtable-style refs (absolute dword) in .rdata-ish region
def dword_refs(t):
    pat=struct.pack("<I",t); out=[];k=0
    buf=data[BASE-LO:END-LO]
    while True:
        k=buf.find(pat,k)
        if k<0: break
        out.append(BASE+k); k+=1
    return out
print()
for t in (0x00B765A0,0x00BA4430):
    r=dword_refs(t); print("0x%08X  dword refs = %d %s"%(t,len(r),", ".join("0x%X"%x for x in r[:6])))
