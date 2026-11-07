import pefile,re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
s=[x for x in pe.sections if x.Name.rstrip(b'\0')==b'.idata2'][0]
raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
i=raw.find(b'WS2_32.dll')
print('WS2_32 marker at rva',hex(s.VirtualAddress+i))
seg=raw[i:i+0x600]
j=0
while j<len(seg):
    e=seg.find(b'\0',j)
    if e<0: break
    t=seg[j:e]
    if len(t)>=3 and all(32<=c<127 for c in t):
        print('  %#010x %s'%(s.VirtualAddress+i+j,t.decode()))
    j=e+1
