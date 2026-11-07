import re
d=open(r"COD OL\codoMP_client_shipRetailBase.dll","rb").read()
def ctx(off, back=0x120, fwd=0x300):
    s=max(0,off-back); e=min(len(d),off+fwd)
    seg=d[s:e]; base=s
    print("=== around 0x%06X ==="%off)
    i=0
    while i<len(seg):
        j=i
        while j<len(seg) and 32<=seg[j]<127: j+=1
        if j-i>=4:
            print("  0x%06X  %r"%(base+i, seg[i:j].decode("latin1")[:120])); i=j
        else: i+=1
for key in (b"[LoadDriver]--skip load driver", b"DisableDriverInterface", b"LoadDriver OK 001"):
    i=d.find(key)
    print("### %r @ 0x%06X"%(key,i))
    if i>=0: ctx(i)
    print()
