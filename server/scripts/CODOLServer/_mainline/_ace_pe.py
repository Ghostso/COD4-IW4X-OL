import pefile, os
for p in [r"COD OL\ace-ats32.dll", r"COD OL\ACE-DRV32.dll", r"COD OL\TP3Helper.exe"]:
    try:
        pe=pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                               pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    except Exception as e:
        print(p,"ERR",e); continue
    print("="*68)
    print("%s  size=%d  IB=0x%X  TD=0x%08X"%(os.path.basename(p), os.path.getsize(p), pe.OPTIONAL_HEADER.ImageBase, pe.FILE_HEADER.TimeDateStamp))
    if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
        e=pe.DIRECTORY_ENTRY_EXPORT
        print("  EXPORT name=%s n=%d"%(e.name, len(e.symbols)))
        for s in e.symbols[:20]: print("     ord %-4s 0x%X %s"%(s.ordinal,s.address,(s.name or b'').decode()))
    else: print("  EXPORT: none")
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            print("  IMP %-22s %d"%(imp.dll.decode(), len(imp.imports)))
