import pefile,re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
s=[x for x in pe.sections if x.Name.rstrip(b"\0")==b'.idata2'][0]
raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
names=re.findall(rb'\x00([A-Za-z_][A-Za-z0-9_]{2,60})\x00', raw)
print('names',len(names))
keys=[b'socket',b'send',b'recv',b'connect',b'wsa',b'select',b'bind',b'listen',b'accept',b'ioctl',b'htons',b'inet_',b'gethost',b'getaddr',b'shutdown',b'closesock']
sel=sorted(set(n.decode() for n in names if any(k in n.lower() for k in keys)))
print('net names',len(sel))
for n in sel: print('  ',n)
