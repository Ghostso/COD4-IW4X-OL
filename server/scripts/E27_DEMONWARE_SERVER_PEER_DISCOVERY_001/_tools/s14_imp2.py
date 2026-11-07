import pefile
from pathlib import Path
ROOT=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"
mods=[(r"native\bin2697\codol_dedrun.exe","codol_dedrun.exe"),("client_room2697.dll","client_room2697.dll"),
      ("client_native_loopback.dll","client_native_loopback.dll"),("client_loopback_guard.exe","client_loopback_guard.exe")]
for rel,name in mods:
    p=str(Path(ROOT)/rel)
    pe=pefile.PE(p)   # full load
    print("=== %s ==="%name)
    imps=sorted({e.dll.decode() for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])})
    print("  imports(%d): %s"%(len(imps),imps))
    note=[]
    for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        for i in e.imports:
            nm=(i.name or b'').decode(errors='replace')
            if any(k in nm.lower() for k in ('socket','send','recv','connect','bind','wsastartup','accept','listen')):
                note.append(e.dll.decode()+":"+nm)
    print("  net-imports:",note[:15])
    exps=getattr(pe,'DIRECTORY_ENTRY_EXPORT',None)
    if exps and getattr(exps,'symbols',None):
        names=[s.name.decode(errors='replace') for s in exps.symbols if s.name]
        print("  exports(%d): %s"%(len(names),names[:20]))
    else:
        print("  exports: none")
    print()
