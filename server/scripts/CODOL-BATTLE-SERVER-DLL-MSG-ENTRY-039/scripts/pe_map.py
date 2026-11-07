import pefile,struct,json,sys,os
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read()
pe=pefile.PE(data=b,fast_load=False)
print('=== FILE HEADER ===')
print('Machine',hex(pe.FILE_HEADER.Machine),'TimeDateStamp',hex(pe.FILE_HEADER.TimeDateStamp),'Characteristics',hex(pe.FILE_HEADER.Characteristics))
print('=== OPTIONAL HEADER ===')
oh=pe.OPTIONAL_HEADER
print('Magic',hex(oh.Magic),'ImageBase',hex(oh.ImageBase),'SizeOfImage',hex(oh.SizeOfImage),'EntryPoint',hex(oh.AddressOfEntryPoint))
print('SectionAlignment',hex(oh.SectionAlignment),'FileAlignment',hex(oh.FileAlignment))
print('DllCharacteristics',hex(oh.DllCharacteristics))
print('=== DATA DIRECTORIES ===')
names={0:'EXPORT',1:'IMPORT',2:'RESOURCE',3:'EXCEPTION',4:'SECURITY',5:'BASERELOC',6:'DEBUG',7:'ARCHITECTURE',8:'GLOBALPTR',9:'TLS',10:'LOAD_CONFIG',11:'BOUND_IMPORT',12:'IAT',13:'DELAY_IMPORT',14:'COM_DESCRIPTOR'}
for i,d in enumerate(oh.DATA_DIRECTORY):
 if d.VirtualAddress or d.Size:
  print(f'  {i:2d} {names.get(i,"?"):14s} RVA={d.VirtualAddress:#010x} Size={d.Size:#x}')
print('=== SECTIONS ===')
for s in pe.sections:
 nm=s.Name.rstrip(b'\0').decode('latin1')
 print(f'  {nm:9s} VA={s.VirtualAddress:#010x} VS={s.Misc_VirtualSize:#010x} RAW={s.PointerToRawData:#010x} RS={s.SizeOfRawData:#010x} Ch={s.Characteristics:#010x} Entropy={s.get_entropy():.3f}')
print('=== IMPORTS ===')
for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
 print(' DLL',e.dll.decode())
 for imp in e.imports[:200]:
  nm=imp.name.decode() if imp.name else None
  if nm: print('   ',hex(imp.address),nm)
print('=== EXPORTS ===')
if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
 for ex in pe.DIRECTORY_ENTRY_EXPORT.symbols:
  print('  ',hex(ex.address), ex.name.decode() if ex.name else None, ex.ordinal)
else: print('  none')
