import pefile, os, hashlib, struct, sys, json
root = r'COD OL'
for name in ['codoMP_client_shipRetail.exe','codoMP_client_shipRetailBase.dll',
             r'codoMP_client_shipRetail.exe.local\codoMP_client_shipRetailBase.dll',
             r'codoMP_client_shipRetailBase.dll.local\codoMP_client_shipRetailBase.dll']:
    p = os.path.join(root, name)
    st = os.stat(p)
    h = hashlib.sha256(open(p,'rb').read()).hexdigest()
    print(f'--- {name} size={st.st_size} sha256={h}')

def dump(p):
    pe = pefile.PE(p, fast_load=False)
    print('\n===============', os.path.basename(p))
    print('machine', hex(pe.FILE_HEADER.Machine), 'chars', hex(pe.FILE_HEADER.Characteristics))
    print('ImageBase', hex(pe.OPTIONAL_HEADER.ImageBase), 'EntryPoint', hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), 'SizeOfImage', hex(pe.OPTIONAL_HEADER.SizeOfImage))
    print('Subsystem', pe.OPTIONAL_HEADER.Subsystem, 'DllCharacteristics', hex(pe.OPTIONAL_HEADER.DllCharacteristics))
    print('sections:')
    for s in pe.sections:
        print(f'  {s.Name.rstrip(chr(0).encode()).decode("latin1"):10s} VA={s.VirtualAddress:#010x} VSize={s.Misc_VirtualSize:#010x} Raw={s.PointerToRawData:#010x}/{s.SizeOfRawData:#010x} flags={s.Characteristics:#010x}')
    print('imports:')
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            print('  ', e.dll.decode(errors='replace'), 'n=', len(e.imports))
            for imp in e.imports[:40]:
                print('      ', imp.name.decode(errors='replace') if imp.name else f'ord#{imp.ordinal}', hex(imp.address))
    else: print('   NONE')
    print('delay imports:')
    if hasattr(pe,'DIRECTORY_ENTRY_DELAY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
            print('  ', e.dll.decode(errors='replace'), 'n=', len(e.imports))
            for imp in e.imports[:40]:
                print('      ', imp.name.decode(errors='replace') if imp.name else f'ord#{imp.ordinal}', hex(imp.address))
    else: print('   NONE')
    print('exports:')
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
        print('  name=', pe.DIRECTORY_ENTRY_EXPORT.name, 'n=', len(pe.DIRECTORY_ENTRY_EXPORT.symbols))
        for s in pe.DIRECTORY_ENTRY_EXPORT.symbols[:80]:
            print('   ', hex(s.address), s.name.decode(errors='replace') if s.name else f'ord#{s.ordinal}', 'fwd=', getattr(s,'forwarder',None))
    else: print('   NONE')
    print('TLS:')
    if hasattr(pe,'DIRECTORY_ENTRY_TLS') and pe.DIRECTORY_ENTRY_TLS:
        t=pe.DIRECTORY_ENTRY_TLS.struct
        print('  StartVA',hex(t.StartAddressOfRawData),'EndVA',hex(t.EndAddressOfRawData),'Index',hex(t.AddressOfIndex),'Callbacks',hex(t.AddressOfCallBacks))
        try:
            for cb in pe.DIRECTORY_ENTRY_TLS.tls_callbacks: print('   cb',hex(cb))
        except Exception as ex: print('   cb err',ex)
    else: print('   NONE')
    return pe

dump(os.path.join(root,'codoMP_client_shipRetail.exe'))
dump(os.path.join(root,'codoMP_client_shipRetailBase.dll'))
