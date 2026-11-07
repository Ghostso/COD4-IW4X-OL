import pefile, os
for p in [r"C:\Windows\system32\drivers\ACE-BASE.sys",
          r"C:\Windows\system32\drivers\ACE-GAME.sys",
          r"C:\Windows\system32\drivers\ACE-ADVT.sys",
          r"C:\Program Files\AntiCheatExpert\ACE-Service64.exe"]:
    if not os.path.isfile(p): print("MISSING",p); continue
    try:
        pe=pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    except Exception as e:
        print(p,"ERR",e); continue
    print("="*68)
    print("%s  size=%d  IB=0x%X  Machine=0x%X"%(os.path.basename(p), os.path.getsize(p), pe.OPTIONAL_HEADER.ImageBase, pe.FILE_HEADER.Machine))
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            nm=imp.dll.decode()
            fl=[(f.name.decode() if f.name else "ord_%s"%f.ordinal) for f in imp.imports]
            print("  %-16s (%d): %s"%(nm, len(fl), ", ".join(fl[:22])))
