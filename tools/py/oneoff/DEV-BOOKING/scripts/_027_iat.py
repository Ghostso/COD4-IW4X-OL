# -*- coding: utf-8 -*-
import struct, sys
sys.path.insert(0, "DEV-BOOKING/scripts")
from _015_lib import DATA, BASE, cstr
need = {0xCA8114, 0xCA8128, 0xCA8548, 0xCA8364}
for slot in sorted(need):
    off = slot - BASE
    p = struct.unpack_from("<I", DATA, off)[0]
    name = ""
    try:
        if 0x400000 <= p < 0x100000000:
            name = cstr(p)
    except Exception:
        name = ""
    print("IAT 0x%08X -> 0x%08X  %r" % (slot, p, name))
print()
# find closesocket / shutdown imports by scanning the import name strings
for kw in (b"closesocket", b"shutdown", b"WSASocketW", b"WSAConnect", b"sendto", b"WSAEventSelect"):
    i = DATA.find(kw)
    print("%-14s first at file off 0x%X (va 0x%X)" % (kw.decode(), i, (BASE + i) if i >= 0 else 0))
