from pathlib import Path
import pefile
paths=[Path('COD OL/TCLS/Client.exe'),Path('COD OL/TCLS/ClientBase.dll'),Path('WeGame/tgp_daemon.exe')]
for p in paths:
 print('\n'+'='*110); print(p)
 pe=pefile.PE(str(p),fast_load=True); pe.parse_data_directories()
 print('base',hex(pe.OPTIONAL_HEADER.ImageBase),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'image',hex(pe.OPTIONAL_HEADER.SizeOfImage),'ts',hex(pe.FILE_HEADER.TimeDateStamp))
 print('sections',[(s.Name.rstrip(b'\0').decode('ascii','replace'),hex(s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.SizeOfRawData),hex(s.Characteristics)) for s in pe.sections])
 print('IMPORTS')
 for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
  names=[i.name.decode('ascii','replace') if i.name else 'ord:'+str(i.ordinal) for i in e.imports]
  print(' ',e.dll.decode('ascii','replace'),len(names))
  print('   ',', '.join(names))
 ed=getattr(pe,'DIRECTORY_ENTRY_EXPORT',None)
 if ed:
  print('EXPORTS')
  for e in ed.symbols: print(' ',hex(e.address),e.name.decode('ascii','replace') if e.name else 'ord:'+str(e.ordinal))
