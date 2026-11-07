"""Agent 03/04: inspect the ORIGINAL iips.dll import + export directories,
and check whether the generated LocalRM.dll still contains the original bytes
for those directories (i.e. whether a header-only repair can reuse them).

Read-only.
"""
import struct

import pefile

ORIG = r"COD OL\IIPS\iips.dll"
GEN = "LocalRM.dll"

IMPORT_DIR_RVA = 0x3EE3C
IMPORT_DIR_SIZE = 0x104
EXPORT_DIR_RVA = 0x41BD0
EXPORT_DIR_SIZE = 0xB1
IAT_RVA = 0x33000
IAT_SIZE = 0x4AC
LOADCFG_RVA = 0x3B1B0
BASERELOC_RVA = 0x50000
BASERELOC_SIZE = 0x3850


def rva_to_off(pe, rva):
    return pe.get_offset_from_rva(rva)


def main():
    po = pefile.PE(ORIG, fast_load=True)
    pg = pefile.PE(GEN, fast_load=True)
    po.parse_data_directories()

    print("=" * 78)
    print("AGENT 03 — IMPORT DIRECTORY INVENTORY (original iips.dll)")
    print("=" * 78)
    print("IMPORT dir RVA 0x%X size 0x%X -> file offset 0x%X"
          % (IMPORT_DIR_RVA, IMPORT_DIR_SIZE, rva_to_off(po, IMPORT_DIR_RVA)))
    total_iat = 0
    for entry in po.DIRECTORY_ENTRY_IMPORT:
        dll = entry.dll.decode("latin-1")
        n_funcs = len(entry.imports)
        named = sum(1 for i in entry.imports if i.name)
        ordonly = n_funcs - named
        iat_rva = entry.struct.FirstThunk
        oft_rva = entry.struct.OriginalFirstThunk
        total_iat += n_funcs * 4
        print("  %-16s FirstThunk(Origi) RVA 0x%08X  OFT RVA 0x%08X  Name RVA 0x%08X"
              % (dll, iat_rva, oft_rva, entry.struct.Name))
        print("      funcs=%d named=%d ordinal-only=%d" % (n_funcs, named, ordonly))
        # sample a few
        for imp in entry.imports[:6]:
            print("        IAT slot RVA 0x%08X  ->  %s"
                  % (imp.address, imp.name.decode("latin-1") if imp.name else ("ordinal %d" % imp.ordinal)))
        if n_funcs > 6:
            print("        ... (%d more)" % (n_funcs - 6))
    print("  total IAT slots = %d (%d bytes)" % (total_iat / 4, total_iat))

    print()
    print("=" * 78)
    print("AGENT 04 — EXPORT DIRECTORY INVENTORY (original iips.dll)")
    print("=" * 78)
    ed = po.DIRECTORY_ENTRY_EXPORT
    s = ed.struct
    print("  Characteristics      = 0x%08X" % s.Characteristics)
    print("  TimeDateStamp        = 0x%08X" % s.TimeDateStamp)
    print("  Major/MinorVersion   = %d.%d" % (s.MajorVersion, s.MinorVersion))
    print("  Name RVA             = 0x%08X (%s)" % (s.Name, ed.name.decode("latin-1") if ed.name else "?"))
    print("  Base                 = %d" % s.Base)
    print("  NumberOfFunctions    = %d" % s.NumberOfFunctions)
    print("  NumberOfNames        = %d" % s.NumberOfNames)
    print("  AddressOfFunctions   = 0x%08X" % s.AddressOfFunctions)
    print("  AddressOfNames       = 0x%08X" % s.AddressOfNames)
    print("  AddressOfNameOrdinals= 0x%08X" % s.AddressOfNameOrdinals)
    for i, e in enumerate(ed.symbols):
        print("    [%2d] %-40s func RVA 0x%08X  (forwarder=%s)"
              % (i, e.name.decode("latin-1") if e.name else "ordinal", e.address, bool(e.forwarder)))
    if ed.name:
        print("  DLL name string: %s" % ed.name.decode("latin-1"))

    print()
    print("=" * 78)
    print("BYTE-IDENTITY CHECK — does LocalRM.dll still carry original directory bytes?")
    print("=" * 78)
    with open(ORIG, "rb") as f:
        do = f.read()
    with open(GEN, "rb") as f:
        dg = f.read()

    regions = [
        ("IMPORT descriptor+thunks", IMPORT_DIR_RVA, IMPORT_DIR_SIZE),
        ("EXPORT descriptor", EXPORT_DIR_RVA, EXPORT_DIR_SIZE),
        ("IAT", IAT_RVA, IAT_SIZE),
        ("LOAD_CONFIG", LOADCFG_RVA, 0x40),
        ("BASERELOC (first 0x400)", BASERELOC_RVA, 0x400),
    ]
    for label, rva, size in regions:
        oo = rva_to_off(po, rva)
        a = do[oo:oo + size]
        b = dg[oo:oo + size]
        same = (a == b)
        print("  %-24s RVA 0x%08X size 0x%04X  fileoff 0x%08X  identical=%s"
              % (label, rva, size, oo, "YES" if same else "NO"))
        if not same:
            for i in range(len(a)):
                if a[i] != b[i]:
                    print("      first diff at +0x%X: orig=0x%02X gen=0x%02X" % (i, a[i], b[i]))
                    break

    # The generated DLL declares a *new* export dir at 0x3302E which is inside .rdata
    print()
    print("  generated EXPORT dir RVA 0x3302E -> file offset 0x%X"
          % rva_to_off(pg, 0x3302E))
    off = rva_to_off(pg, 0x3302E)
    print("  generated export dir bytes: %s" % dg[off:off + 40].hex())
    for i in range(16):
        d = pg.OPTIONAL_HEADER.DATA_DIRECTORY[i]
        if d.VirtualAddress == 0x3302E:
            print("  (declared as directory index %d)" % i)

    print()
    print("  generated IAT dir RVA 0x33000 -> file offset 0x%X" % rva_to_off(pg, 0x33000))
    off = rva_to_off(pg, 0x33000)
    print("  generated IAT bytes (first 64): %s" % dg[off:off + 64].hex())

    po.close()
    pg.close()


if __name__ == "__main__":
    main()
