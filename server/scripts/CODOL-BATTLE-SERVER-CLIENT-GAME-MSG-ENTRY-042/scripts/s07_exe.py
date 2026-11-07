# -*- coding: utf-8 -*-
"""Enumerate EXE + DLL PE identity, imports, exports, and search for game-net symbols."""
import sys, os, pefile, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
import hashlib

def pe_summary(path, data):
    pe=pefile.PE(data=data, fast_load=False)
    ib=pe.OPTIONAL_HEADER.ImageBase
    print("=== %s ===" % os.path.basename(path))
    print("  size=%d sha256=%s" % (len(data), hashlib.sha256(data).hexdigest()))
    print("  ImageBase=%08x EntryPoint=%08x" % (ib, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print("  sections:", [(s.Name.rstrip(b'\0').decode('latin1'), hex(s.VirtualAddress), hex(s.Misc_VirtualSize)) for s in pe.sections])
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            print("  IMPORT %-20s %d" % (e.dll.decode('latin1'), len(e.imports)))
    else:
        print("  IMPORT (none)")
    if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
        print("  EXPORTS:")
        for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            print("     ord=%d name=%s rva=%08x" % (s.ordinal, s.name.decode('latin1') if s.name else None, s.address))
    return ib

ib_exe = pe_summary(C.EXE, C._bex)
pe_summary(C.DLL, C._b)

# net-related imports in EXE
pe=pefile.PE(data=C._bex, fast_load=False)
ibx=pe.OPTIONAL_HEADER.ImageBase
NET={"ws2_32.dll","wsock32.dll","wininet.dll","winhttp.dll","iphlpapi.dll","dnsapi.dll"}
print("\n=== EXE net imports ===")
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    d=e.dll.decode('latin1').lower()
    if d in NET:
        for im in e.imports:
            print("  %s!%s @%08x"%(e.dll.decode('latin1'), im.name.decode('latin1') if im.name else 'ord', im.address))
