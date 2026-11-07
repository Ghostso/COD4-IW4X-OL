import sys, pefile
for p in sys.argv[1:]:
    pe=pefile.PE(p, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    print("===",p)
    print("  TimeDateStamp 0x%08X"%pe.FILE_HEADER.TimeDateStamp)
    print("  AddrOfEntry 0x%X"%pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
        e=pe.DIRECTORY_ENTRY_EXPORT
        print("  DLLname:", e.name)
        print("  nfuncs",len(e.symbols))
        for s in e.symbols[:25]:
            print("    ord %-6s addr 0x%X name %s"%(s.ordinal, s.address, s.name))
    else:
        print("  NO EXPORT DIRECTORY")
