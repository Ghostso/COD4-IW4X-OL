# -*- coding: utf-8 -*-
"""Unpacked image import table + network APIs. Read-only."""
import sys, os, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
pe=pefile.PE(data=C._b, fast_load=False)
if not hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
    print("no DIRECTORY_ENTRY_IMPORT"); 
else:
    for e in pe.DIRECTORY_ENTRY_IMPORT:
        print("IMPORT %s (%d)" % (e.dll.decode('latin1'), len(e.imports)))
        for im in e.imports[:200]:
            nm = im.name.decode('latin1') if im.name else ("ord_%d"%im.ordinal)
            if any(k in e.dll.decode('latin1').lower() for k in ("ws2","wsock","wininet","winhttp","iphlp","dns")):
                print("   %-30s @%08x" % (nm, im.address))
