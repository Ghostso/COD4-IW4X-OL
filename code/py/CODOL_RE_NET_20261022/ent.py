import pefile, struct, math, collections
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
def ent(b):
    if not b: return 0
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
for s in pe.sections:
    nm=s.Name.rstrip(b"\0").decode()
    raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    print("  %-10s raw=%#x ent=%.3f unique=%d" % (nm,len(raw),ent(raw),len(set(raw))))
