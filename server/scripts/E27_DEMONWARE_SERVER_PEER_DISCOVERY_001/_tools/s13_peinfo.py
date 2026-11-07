import pefile, hashlib
from pathlib import Path
ROOT=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"
mods=[(r"native\bin2697\codol_dedrun.exe","codol_dedrun.exe"),("client_room2697.dll","client_room2697.dll"),
      ("client_native_loopback.dll","client_native_loopback.dll"),("client_loopback_guard.exe","client_loopback_guard.exe")]
for rel,name in mods:
    p=str(Path(ROOT)/rel); d=Path(p).read_bytes()
    pe=pefile.PE(p,fast_load=True)
    print("=== %s ==="%name)
    print("  size=%d sha256=%s"%(len(d),hashlib.sha256(d).hexdigest()))
    print("  machine=%04X IB=%08X SizeOfImage=%08X EP=%08X subsys=%d"%(
        pe.FILE_HEADER.Machine, pe.OPTIONAL_HEADER.ImageBase, pe.OPTIONAL_HEADER.SizeOfImage,
        pe.OPTIONAL_HEADER.AddressOfEntryPoint, pe.OPTIONAL_HEADER.Subsystem))
    print("  sections:", [(s.Name.rstrip(b'\0').decode(errors='replace'),hex(s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.SizeOfRawData)) for s in pe.sections])
    print("  imports:", sorted({e.dll.decode() for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])}))
    # any notable net/crypto imports
    note=[]
    for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        for i in e.imports:
            nm=(i.name or b'').decode(errors='replace')
            if any(k in nm.lower() for k in ('socket','send','recv','connect','bind','wsastartup','crypt','ssl','tls','getprocaddress','loadlibrary')):
                note.append(e.dll.decode()+":"+nm)
    print("  notable:", note[:20])
    print()
