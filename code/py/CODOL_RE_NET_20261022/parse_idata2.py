import pefile, struct
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
s=[x for x in pe.sections if x.Name.rstrip(b"\0")==b'.idata2'][0]
base=s.VirtualAddress; raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
def getstr(rva):
    o=s.PointerToRawData+(rva-base)
    if o<0 or o>len(d): return None
    e=d.find(b"\0",o)
    return d[o:e].decode('latin1','replace')
print('section',hex(base),hex(len(raw)))
# find candidate descriptor tables: sequences of 20 bytes where fields look like RVAs in [base,base+size)
cands=[]
for i in range(0,len(raw)-20,4):
    oft,ts,fc,name,ft=struct.unpack_from('<IIIII',raw,i)
    if (oft|ts|fc|name|ft)==0: continue
    if base<=name<base+len(raw):
        cands.append(i)
print('candidate descriptor starts',len(cands))
i=0
groups=[]
cur=[]
while i<=len(raw)-20:
    oft,ts,fc,name,ft=struct.unpack_from('<IIIII',raw,i)
    if (oft|ts|fc|name|ft)==0:
        if cur: groups.append(cur); cur=[]
        i+=20; continue
    if base<=name<base+len(raw) and base<=oft<base+len(raw):
        cur.append((i,oft,ts,fc,name,ft)); i+=20
    else:
        i+=4
if cur: groups.append(cur)
print('groups',len(groups))
for g in groups:
    print('\n--- group at %#x, %d entries' % (g[0][0], len(g)))
    for (off,oft,ts,fc,name,ft) in g:
        print('   entry off=%#x OFT=%#x FT=%#x Name=%#x  -> %s' % (off,oft,ft,name,getstr(name)))
        # dump thunks
        th=oft; cnt=0; names=[]
        while cnt<40:
            o=s.PointerToRawData+(th-base)
            if o+4>len(raw): break
            v=struct.unpack_from('<I',raw,o)[0]
            if v==0: break
            if v & 0x80000000: names.append('ord#%d'%(v&0xffff))
            else:
                nm=getstr(v+2)
                names.append(nm)
            th+=4; cnt+=1
        print('      ',', '.join(names[:40]))
