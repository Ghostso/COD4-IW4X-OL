# EX-065 PHASE 3: recover the TCLS_SHAREDMEMEMORY+GamePID protocol from
# TenProxy.dll and cross-check against the historical TenProxy logs.
import json
import os
import re

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

TP = r"工具\EX035_DIR\TenProxy.dll"


def main():
    pe = pefile.PE(TP, fast_load=True)
    pe.parse_data_directories()
    data = open(TP, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase
    print("=" * 78)
    print("TenProxy.dll  base 0x%X  size 0x%X" % (
        base, pe.OPTIONAL_HEADER.SizeOfImage))
    print("=" * 78)

    print()
    print("TCLS-related strings:")
    for m in re.finditer(rb"[ -~]{4,}", data):
        s = m.group()
        if b"TCLS" in s or b"SHAREDMEM" in s or b"GamePID" in s:
            print("  @0x%06X  %r" % (m.start(), s[:120]))
    print()
    print("UTF-16LE TCLS strings:")
    seen = set()
    for m in re.finditer(rb"(?:[ -~]\x00){3,}", data):
        try:
            s = m.group().decode("utf-16-le")
        except Exception:
            continue
        if "TCLS" in s or "SHAREDMEM" in s or "GamePID" in s:
            if s in seen:
                continue
            seen.add(s)
            print("  @0x%06X  %r" % (m.start(), s))

    print()
    print("=" * 78)
    print("imports of interest")
    print("=" * 78)
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in d.imports:
            nm = imp.name.decode() if imp.name else "ord%d" % imp.ordinal
            if any(k in nm for k in ("FileMapping", "MapView", "Mutex",
                                     "Event", "ProcessId", "LoadLibrary",
                                     "GetProcAddress", "PostMessage",
                                     "FindWindow", "CreateFile")):
                print("  %-28s IAT VA 0x%08X  %s!%s" % (
                    "", base + (imp.address - base), d.dll.decode(), nm))


if __name__ == "__main__":
    main()
