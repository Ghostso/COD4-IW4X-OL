import pefile,struct
ws=r'C:\Windows\SysWOW64\ws2_32.dll'
pe=pefile.PE(ws)
ex={s.address:s.name.decode() for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
for r,n in sorted(ex.items()): print('%#08x %s'%(r,n))
