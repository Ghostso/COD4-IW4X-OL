import pefile
from pathlib import Path
for p in [Path(r'COD OL\codoMP_client_shipRetail.exe'),Path(r'COD OL\TenProxy.dll'),Path(r'WeGame\tgp_daemon.exe')]:
 print('\n###',p)
 try:
  pe=pefile.PE(str(p),fast_load=False)
  print('timestamp',hex(pe.FILE_HEADER.TimeDateStamp),'image',hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry',hex(pe.OPTIONAL_HEADER.ImageBase+pe.OPTIONAL_HEADER.AddressOfEntryPoint))
  for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
   names=[]
   for i in e.imports:
    if i.name: names.append(i.name.decode(errors='replace'))
   print(e.dll.decode(errors='replace'),', '.join(names))
 except Exception as ex: print('ERR',ex)
