import pefile
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe=pefile.PE(S)
print("=== server imports ===")
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    print("  %s (%d)"%(e.dll.decode(),len(e.imports)))
print()
print("=== server TLS dir / sections ===")
for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
    if d.VirtualAddress: print("  name=%s rva=%08X size=%08X"%(d.name,d.VirtualAddress,d.Size))
