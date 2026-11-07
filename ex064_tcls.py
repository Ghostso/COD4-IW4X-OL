# EX-064 TASK H/K: TCLS is the candidate external entry. Verify.
import json
import os
import re

import pefile

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    if not os.path.exists(TCLS):
        print("MISSING %s" % TCLS)
        return
    pe = pefile.PE(TCLS, fast_load=True)
    pe.parse_data_directories()
    base = pe.OPTIONAL_HEADER.ImageBase
    data = open(TCLS, "rb").read()
    print("=" * 78)
    print("tcls_core.exe  base 0x%X  size 0x%X  sha256 %s" % (
        base, pe.OPTIONAL_HEADER.SizeOfImage,
        __import__("hashlib").sha256(data).hexdigest()[:32]))
    print("=" * 78)

    print()
    print("imports:")
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for d in pe.DIRECTORY_ENTRY_IMPORT:
            nm = d.dll.decode(errors="replace")
            print("   %s" % nm)
            for imp in d.imports:
                n = imp.name.decode() if imp.name else "ord%d" % imp.ordinal
                if any(k in n for k in ("IIPS", "Resource", "iips")):
                    print("        %-30s IAT RVA 0x%X" % (n, imp.address - base))
    else:
        print("   (no imports)")

    print()
    print("=" * 78)
    print("IIPS-related strings in tcls_core.exe")
    print("=" * 78)
    seen = set()
    for m in re.finditer(rb"[ -~]{4,}", data):
        s = m.group()
        if b"iips" in s.lower() or b"IIPS" in s or b"ResourceManager" in s \
                or b"ifs2" in s.lower() or b"LaunchRestore" in s:
            if s in seen:
                continue
            seen.add(s)
            print("   @0x%06X  %r" % (m.start(), s[:120]))

    print()
    print("=" * 78)
    print("does tcls_core.exe import iips.dll or IIPSLaunchRestore.dll?")
    print("=" * 78)
    names = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        names += [d.dll.decode(errors="replace") for d in pe.DIRECTORY_ENTRY_IMPORT]
    if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
        names += [d.dll.decode(errors="replace")
                  for d in pe.DIRECTORY_ENTRY_DELAY_IMPORT]
    hits = [n for n in names if "iips" in n.lower() or "restore" in n.lower()]
    print("   matching imports: %s" % (hits or "NONE"))
    print("   total imports: %d" % len(names))

    print()
    print("=" * 78)
    print("LoadLibrary / GetProcAddress presence")
    print("=" * 78)
    for s in (b"LoadLibraryA", b"LoadLibraryW", b"GetProcAddress",
              b"GetProcAddressEx"):
        print("   %-18s x%d" % (s.decode(), data.count(s)))


if __name__ == "__main__":
    main()
