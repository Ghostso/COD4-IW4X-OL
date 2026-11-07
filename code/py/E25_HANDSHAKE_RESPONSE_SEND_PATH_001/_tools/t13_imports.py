import pefile
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P)
print("=== imported DLLs / interesting send APIs ===")
want=("send","sendto","WSASend","WSASendTo","TransmitFile","HttpSendRequest","select")
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    dll=e.dll.decode()
    names=[]
    try:
        for imp in e.imports:
            nm=(imp.name or b"").decode(errors="replace")
            if any(w.lower() in nm.lower() for w in want): names.append(nm)
    except Exception as ex: pass
    if names or dll.lower().startswith("ws2") or "wininet" in dll.lower() or "winhttp" in dll.lower():
        print("  %-24s %s"%(dll, names))
print()
print("total imports:", [(e.dll.decode() if isinstance(e.dll,bytes) else e.dll) for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[])])
