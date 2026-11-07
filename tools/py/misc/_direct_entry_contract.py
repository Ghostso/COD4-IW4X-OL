import sys,pathlib,json,hashlib
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import pefile
for name in ['codoMP_client_shipRetail.exe','codoMP_client_shipRetailBase.dll']:
 p=pathlib.Path('COD OL')/name; pe=pefile.PE(str(p),fast_load=False)
 print('\n',name)
 if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
  print('exports count',len(pe.DIRECTORY_ENTRY_EXPORT.symbols))
  for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
   if s.ordinal in (1,2,3):
    print(' ord',s.ordinal,'rva',hex(s.address) if s.address is not None else None,'va',hex(pe.OPTIONAL_HEADER.ImageBase+(s.address or 0)),'name',s.name)
  print('first20')
  for s in pe.DIRECTORY_ENTRY_EXPORT.symbols[:20]:
   print(' ',s.ordinal,hex(s.address) if s.address is not None else None,s.name)
 if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
  print('imports')
  for e in pe.DIRECTORY_ENTRY_IMPORT:
   print(' ',e.dll)
   for i in e.imports: print('   ',i.name,i.ordinal,hex(i.address))
