import pefile,re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
s=[x for x in pe.sections if x.Name.rstrip(b"\0")==b'.idata2'][0]
raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
base=s.VirtualAddress
# find ascii names
out=[]
for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_@?$]{2,80}', raw):
    st=m.start()
    if st<2: continue
    hint=int.from_bytes(raw[st-2:st],'little')
    # preceding byte should be end of previous name (nul) or start
    nm=m.group().decode('latin1')
    out.append((base+st,nm,hint))
print('candidate names',len(out))
keys=['socket','send','recv','connect','wsa','select','bind','listen','accept','ioctl','htons','inet_','gethost','getaddr','shutdown','closesock','Send','Recv','Socket']
seen=set()
for rva,nm,hint in out:
    if any(k in nm for k in keys) and nm not in seen:
        seen.add(nm); print('  %#010x hint=%d %s' % (rva,hint,nm))
print('\n--- total unique',len(set(x[1] for x in out)))
print('\nfirst 40:')
for rva,nm,hint in out[:40]: print('  %#010x %d %s' % (rva,hint,nm))
