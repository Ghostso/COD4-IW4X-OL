import pefile,re,os
p=r'COD OL\VSDDrvDll.dll'
d=open(p,'rb').read(); pe=pefile.PE(p)
print('exports:')
for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    print('  ',hex(s.address), s.name.decode(errors='replace') if s.name else 'ord#%d'%s.ordinal)
print('\nstrings (net-ish):')
pat=re.compile(rb'[\x20-\x7e]{6,}')
keys=[b'vWINHTTP',b'TCLS',b'socket',b'connect',b'netchan',b'NET_',b'codol',b'CODOL',b'TenProxy',b'VSD',b'GAME',b'game',b'lobby',b'auth',b'3074',b'proxy',b'Proxy']
seen=set()
for m in pat.finditer(d):
    s=m.group()
    if any(k in s for k in keys):
        t=s.decode('latin1')
        if t not in seen:
            seen.add(t); print('   %#x %s'%(m.start(),t[:120]))
        if len(seen)>120: break
