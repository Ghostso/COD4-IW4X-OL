# EX-064 TASK H/J: check whether the TCLS extern entry connects to the known
# CODOL native bootstrap addresses, and record the boundary.
import json
import os

import pefile

NATIVE = {
    0x77F580: "existing native bootstrap dispatcher",
    0x77F8B3: "existing native bootstrap",
    0x4FD9B0: "existing native bootstrap",
    0x4FCEE0: "existing native bootstrap",
    0x808650: "existing native bootstrap",
    0x7E98F0: "existing native bootstrap",
    0x6212C0: "existing native bootstrap (STUN/argv gate consumer)",
}

MODS = [
    ("codoMP_client_shipRetail.exe", r"工具\EX035_DIR\codoMP_client_shipRetail.exe"),
    ("codoMP_client_shipRetailBase.dll", r"工具\EX035_DIR\codoMP_client_shipRetailBase.dll"),
    ("tcls_core.exe", r"WeGame\tcls\tcls_core.exe"),
    ("IIPSLaunchRestore.dll", r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"),
]


def main():
    print("=" * 78)
    print("does any module import both the iips-family exports AND the")
    print("known native bootstrap module?")
    print("=" * 78)
    for label, path in MODS:
        if not os.path.exists(path):
            print("  %-32s MISSING" % label)
            continue
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories()
        names = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            names += [d.dll.decode(errors="replace")
                      for d in pe.DIRECTORY_ENTRY_IMPORT]
        if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
            names += [d.dll.decode(errors="replace")
                      for d in pe.DIRECTORY_ENTRY_DELAY_IMPORT]
        exps = []
        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            exps = [e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols
                    if e.name]
        print()
        print("  %s" % label)
        print("     imports (%d): %s" % (len(names), ", ".join(names[:14])))
        print("     exports (%d): %s" % (len(exps), ", ".join(exps[:10])))

    print()
    print("=" * 78)
    print("known native bootstrap addresses: present as immediates in which")
    print("module, and at what RVA?")
    print("=" * 78)
    for label, path in MODS:
        if not os.path.exists(path):
            continue
        data = open(path, "rb").read()
        pe = pefile.PE(path, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        print()
        print("  %s (base 0x%X)" % (label, base))
        for va, note in sorted(NATIVE.items()):
            n = data.count(va.to_bytes(4, "little"))
            if n:
                print("     0x%X x%d   (%s)" % (va, n, note))
        # also absolute-free: since these are EXE VAs, only modules with the
        # same base could use them literally
        if base != 0x400000:
            print("     (base != 0x400000 -> EXE-VA immediates not applicable)")


if __name__ == "__main__":
    main()
