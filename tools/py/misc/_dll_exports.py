import pefile
exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll"
pe = pefile.PE(exe, fast_load=True)
print("exports:")
if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        print("  %s  RVA=0x%X" % (e.name.decode() if e.name else "ord=%d" % e.ordinal, e.address))