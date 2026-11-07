import pefile, os, sys
root = r"COD OL\IIPS"
targets = ["iips.dll","IIPSHost.dll","IFS2.dll","IIPSVFS.dll","IIPSCheck.dll","IIPSRepair.dll","IIPSStats.dll","IIPSLaunchRestore.dll","iips_policymsg.dll","Download.dll","p2papp.dll","IIPSHostApp.exe"]
for t in targets:
    p = os.path.join(root,t)
    if not os.path.isfile(p):
        print("MISSING", t); continue
    try:
        pe = pefile.PE(p, fast_load=True)
    except Exception as e:
        print("ERR", t, e); continue
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    print("="*70)
    print("%s  size=%d  ImageBase=0x%X  Entry=0x%X" % (t, os.path.getsize(p), pe.OPTIONAL_HEADER.ImageBase, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
        e=pe.DIRECTORY_ENTRY_EXPORT
        print("  EXPORT dllname=%s  n=%d" % (e.name, len(e.symbols)))
        for s in e.symbols[:40]:
            print("     ord %-5s 0x%X  %s" % (s.ordinal, s.address, s.name))
    else:
        print("  EXPORT: none")
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        print("  IMPORTS:")
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            nm = imp.dll.decode("latin1")
            funcs = []
            for f in imp.imports:
                if f.name: funcs.append(f.name.decode("latin1"))
                else: funcs.append("ord_%s"%f.ordinal)
            print("     %-24s %d" % (nm, len(funcs)))
