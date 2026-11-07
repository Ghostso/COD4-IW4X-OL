import sys, pefile
from capstone import *
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=Path('COD OL')
exe=pefile.PE(str(root/'codoMP_client_shipRetail.exe'), fast_load=False)
base=pefile.PE(str(root/'codoMP_client_shipRetailBase.dll'), fast_load=False)
print('EXE import entries')
for ent in getattr(exe,'DIRECTORY_ENTRY_IMPORT',[]):
 print('dll',ent.dll)
 for imp in ent.imports: print(' ',imp.name,imp.ordinal,hex(imp.address))
print('\nEXE TLS')
if hasattr(exe,'DIRECTORY_ENTRY_TLS'):
 t=exe.DIRECTORY_ENTRY_TLS.struct
 print('start',hex(t.StartAddressOfRawData),'end',hex(t.EndAddressOfRawData),'index',hex(t.AddressOfIndex),'callbacks',hex(t.AddressOfCallBacks))
 try: print('callbacks',[hex(x) for x in exe.DIRECTORY_ENTRY_TLS.callbacks])
 except Exception as e: print('callback parse',e)
print('\nEXE exception entries count',len(getattr(exe,'DIRECTORY_ENTRY_EXCEPTION',[])))
print('\nBase exports')
for sym in base.DIRECTORY_ENTRY_EXPORT.symbols: print(sym.ordinal,sym.name,hex(sym.address))
print('\nBase import entries')
for ent in getattr(base,'DIRECTORY_ENTRY_IMPORT',[]):
 print('dll',ent.dll)
 for imp in ent.imports: print(' ',imp.name,imp.ordinal,hex(imp.address))
print('\nBase TLS')
if hasattr(base,'DIRECTORY_ENTRY_TLS'):
 t=base.DIRECTORY_ENTRY_TLS.struct
 print('start',hex(t.StartAddressOfRawData),'end',hex(t.EndAddressOfRawData),'index',hex(t.AddressOfIndex),'callbacks',hex(t.AddressOfCallBacks))
 try: print('callbacks',[hex(x) for x in base.DIRECTORY_ENTRY_TLS.callbacks])
 except Exception as e: print('callback parse',e)
print('\nBase exception count',len(getattr(base,'DIRECTORY_ENTRY_EXCEPTION',[])))
for pe,label,rva,n in [(exe,'EXE_ENTRY',exe.OPTIONAL_HEADER.AddressOfEntryPoint,80),(base,'BASE_E1',0x1d6582c,160),(base,'BASE_ENTRY',base.OPTIONAL_HEADER.AddressOfEntryPoint,120)]:
 print('\nDIS',label,hex(pe.OPTIONAL_HEADER.ImageBase+rva))
 data=pe.get_memory_mapped_image()
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for ins in md.disasm(data[rva:rva+n],pe.OPTIONAL_HEADER.ImageBase+rva): print(f'{ins.address:08X} {ins.bytes.hex(" "):30} {ins.mnemonic:8} {ins.op_str}')
