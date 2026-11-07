import sys, pefile
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
S=pefile.PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe",fast_load=True)
S.parse_data_directories()
IB=S.OPTIONAL_HEADER.ImageBase
# map IAT entry VA -> (dll, name)
iat={}
for e in S.DIRECTORY_ENTRY_IMPORT:
    dll=e.dll.decode()
    for imp in e.imports:
        if imp.address:
            iat[imp.address]=(dll, (imp.name or b"").decode("latin1"))
print("=== resolve the IAT thunks used by the writer ===")
for tgt in (0x160bf8e0,0x160bf8e4,0x160bf8e8,0x160bf8ec,0x160bf8f0):
    print("  [0x%X] -> %s" % (tgt, iat.get(tgt,"(unresolved)")))
print()
print("=== all imports whose IAT address is near 0x160bf8e0 ===")
for a in sorted(iat):
    if 0x160bf800<=a<=0x160bfa00:
        print("  0x%X %s!%s" % (a, iat[a][0], iat[a][1]))