import pefile, hashlib, sys
p = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
h = hashlib.sha256(open(p,'rb').read()).hexdigest().upper()
pe = pefile.PE(p, fast_load=True)
pe.parse_data_directories()
print('sha256', h)
print('num_dd', pe.OPTIONAL_HEADER.NumberOfRvaAndSizes)
imps = pe.DIRECTORY_ENTRY_IMPORT or []
print('import_dlls', len(imps))
for e in imps:
    print('IMPORT DLL', e.dll.decode(errors='replace'), 'entries', len(e.imports))
print('sections:')
for s in pe.sections:
    n = s.Name.decode(errors='replace').strip()
    print('  %-10s VA=%s VS=%s RAW=%s PTR=%s X=%s' % (n, hex(s.VirtualAddress), hex(s.Misc_VirtualSize), hex(s.SizeOfRawData), hex(s.PointerToRawData), bool(s.Characteristics & 0x20000000)))
