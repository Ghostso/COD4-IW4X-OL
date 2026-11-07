import pefile
for p in [r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll']:
    pe = pefile.PE(p, fast_load=True)
    pe.parse_data_directories()
    print('file', p)
    print('machine', hex(pe.FILE_HEADER.Machine), 'imagebase', hex(pe.OPTIONAL_HEADER.ImageBase))
    imps = pe.DIRECTORY_ENTRY_IMPORT or []
    print('import_dlls', len(imps))
    for e in imps:
        print('IMPORT', e.dll.decode(errors='replace'), 'entries', len(e.imports))
        for imp in e.imports[:20]:
            print('   ', imp.name, hex(imp.address))
    print('sections:')
    for s in pe.sections:
        n=s.Name.decode(errors='replace').strip()
        print('  %-10s VA=%s VS=%s RAW=%s PTR=%s X=%s' % (n,hex(s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.SizeOfRawData),hex(s.PointerToRawData),bool(s.Characteristics & 0x20000000)))
