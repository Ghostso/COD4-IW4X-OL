from pathlib import Path
import pefile, struct
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL')
for fn in ['codoMP_client_shipRetail.exe','codoMP_client_shipRetailBase.dll']:
    p=root/fn
    pe=pefile.PE(str(p), fast_load=True)
    print('\n###',fn)
    print('base',hex(pe.OPTIONAL_HEADER.ImageBase),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'size',hex(pe.OPTIONAL_HEADER.SizeOfImage))
    for s in pe.sections:
        nm=s.Name.rstrip(b'\x00').decode('latin1','replace')
        print(nm,hex(s.VirtualAddress),hex(max(s.Misc_VirtualSize,s.SizeOfRawData)),hex(s.Characteristics),hex(s.PointerToRawData))
    d=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
    terms=[b'WIN_NO_TCLS',b'IsTCLSLogOn',b'TP3Helper.exe',b'TQMCenter.exe',b'BugTrace.dll',b'VSDDrvDll.dll',b'ACE-DRV32.dll',b'GetCommandLineW',b'GetCommandLineA',b'GetEnvironmentVariableW',b'CreateProcessW',b'CreateFileW',b'CreateFileMappingW',b'OpenFileMappingW',b'MapViewOfFile',b'LoadLibraryA',b'GetProcAddress',b'libcef.dll',b'cef_string_utf16_clear']
    for t in terms:
        hits=[]
        pos=0
        while True:
            i=d.find(t,pos)
            if i<0: break
            try:
                sec=pe.get_section_by_rva(pe.get_rva_from_offset(i)).Name.rstrip(b'\x00').decode('latin1','replace')
            except Exception:
                sec='?'
            hits.append((hex(base+pe.get_rva_from_offset(i)),sec))
            pos=i+1
        if hits:
            print(t.decode('latin1','replace'),hits[:20],'n=',len(hits))
