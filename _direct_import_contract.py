import sys, pathlib, hashlib, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pefile
root=pathlib.Path('COD OL')
for name in ['codoMP_client_shipRetail.exe','TenProxy.dll','codoMP_client_shipRetailBase.dll']:
    p=root/name
    pe=pefile.PE(str(p), fast_load=False)
    print('\n=====',name,'sha256',hashlib.sha256(p.read_bytes()).hexdigest(),'=====')
    print('machine',hex(pe.FILE_HEADER.Machine),'ts',hex(pe.FILE_HEADER.TimeDateStamp),'base',hex(pe.OPTIONAL_HEADER.ImageBase),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'sizeimage',hex(pe.OPTIONAL_HEADER.SizeOfImage))
    print('imports:')
    for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        print(' ', (ent.dll or b'').decode('ascii','replace'))
        for imp in ent.imports:
            nm=imp.name.decode('ascii','replace') if imp.name else None
            print('   ', ('ordinal'+str(imp.ordinal)) if nm is None else nm, 'iat_va',hex(imp.address))
    print('tls:', hasattr(pe,'DIRECTORY_ENTRY_TLS'))
    if hasattr(pe,'DIRECTORY_ENTRY_TLS'):
        t=pe.DIRECTORY_ENTRY_TLS.struct
        print(' ',hex(t.AddressOfCallBacks), [hex(x) for x in getattr(pe.DIRECTORY_ENTRY_TLS,'callbacks',[])])
