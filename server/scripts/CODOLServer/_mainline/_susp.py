import pefile
for f in [r"COD OL\IIPS\Download.dll", r"COD OL\IIPS\p2papp.dll", r"COD OL\IIPS\IIPSHost.dll"]:
    pe=pefile.PE(f, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    print("="*70); print(f, pe.FILE_HEADER.TimeDateStamp)
    for imp in pe.DIRECTORY_ENTRY_IMPORT:
        nm=imp.dll.decode()
        if nm.upper().startswith(("WLDAP","WININET","WINHTTP","DNSAPI","URLMON","SSPI","CRYPT")):
            fl=[(x.name.decode() if x.name else "ord_%s"%x.ordinal) for x in imp.imports]
            print("  %-16s %d: %s"%(nm, len(fl), ", ".join(fl[:20])))
