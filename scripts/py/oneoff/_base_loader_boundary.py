from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll')
pe=pefile.PE(str(p), fast_load=False)
print('base',hex(pe.OPTIONAL_HEADER.ImageBase),'entry_rva',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for idx,name in [(pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],'IMPORT'),(pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT'],'DELAY_IMPORT'),(pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_TLS'],'TLS'),(pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],'EXPORT')]:
    d=pe.OPTIONAL_HEADER.DATA_DIRECTORY[idx]
    print(name,hex(d.VirtualAddress),hex(d.Size))
for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
    print('IMPORT_DLL',ent.dll.decode('latin1','replace'))
    for imp in ent.imports:
        print(' ',imp.name.decode('latin1','replace') if imp.name else 'ordinal %d'%imp.ordinal,hex(imp.address))
print('delay',len(getattr(pe,'DIRECTORY_ENTRY_DELAY_IMPORT',[])))
exp=getattr(pe,'DIRECTORY_ENTRY_EXPORT',None)
if exp:
    for s in exp.symbols:
        sec=pe.get_section_by_rva(s.address)
        print('EXPORT',s.ordinal,hex(s.address),sec.Name.rstrip(b'\x00').decode('latin1','replace') if sec else '?',s.name.decode('latin1','replace') if s.name else None)
tls=getattr(pe,'DIRECTORY_ENTRY_TLS',None)
if tls:
    print('TLS',hex(tls.struct.AddressOfCallBacks),tls.struct.AddressOfCallBacks)
print('ENTRY_DISASM')
img=pe.get_memory_mapped_image(); rva=pe.OPTIONAL_HEADER.AddressOfEntryPoint
for ins in Cs(CS_ARCH_X86,CS_MODE_32).disasm(img[rva:rva+256],pe.OPTIONAL_HEADER.ImageBase+rva):
    print('%08X %-24s %-8s %s'%(ins.address-pe.OPTIONAL_HEADER.ImageBase,ins.bytes.hex(),ins.mnemonic,ins.op_str))
