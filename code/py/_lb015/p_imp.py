import pefile
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
pe = pefile.PE(p, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
for e in pe.DIRECTORY_ENTRY_IMPORT:
    print("DLL:", e.dll.decode(errors='replace'))
    for imp in e.imports[:80]:
        print("    ", imp.name.decode() if imp.name else "ord%d"%imp.ordinal)
