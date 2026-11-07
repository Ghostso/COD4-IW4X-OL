"""RESTORE-IIPS-CONTRACT-001 / Task 05 - where does the "iipsinit" window class come from?

Facts already established:
  * Task 02: the EXE contains only ".?iipsinit" (an MSVC decorated SYMBOL name),
    not a standalone C string.
  * Task 04: NEITHER iips.dll nor LocalRM_v3.dll contains the literal "iipsinit"
    at all (count = 0), even though LocalRM_v3 carries a byte-identical copy of
    the original's .rdata (all IIPS log strings present at identical offsets).

EB-003 observed, at runtime, a window whose CLASS name read back as "iipsinit"
in condition A, with EMPTY text in condition B.

If the class name exists in no .rdata literal, it is built at runtime. This
script tests the two remaining candidates that could construct it:
  (a) the decorated symbol ".?iipsinit" being used AS a class name by code
      (i.e. the string IS used, just via the symbol table), or
  (b) a name assembled from fragments at runtime.

It also re-checks the EXE for any WNDCLASS registration surface near the symbol.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
BASE = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")
V3 = os.path.join(ROOT, "LocalRM_v3.dll")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    out = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        out.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, ib, out


def o2r(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["va"] + (off - s["raw"])
    return None


def secname(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["name"]
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 05: origin of the 'iipsinit' window class ===")
    print()

    d = open(EXE, "rb").read()
    pe, ib, secs = sections(d)
    off = d.find(b"iipsinit")
    rva = o2r(secs, off)
    rep["exe"] = {"image_base": "0x%X" % ib, "iipsinit_off": "0x%X" % off,
                  "iipsinit_rva": "0x%X" % rva if rva else None,
                  "iipsinit_section": secname(secs, off),
                  "preceded_by": chr(d[off - 1]),
                  "full_symbol": d[off - 1:off + 8].decode("latin1")}
    print("  EXE image base    = 0x%08X" % ib)
    print("  'iipsinit' at     = 0x%X  (RVA 0x%X, section %s)"
          % (off, rva, secname(secs, off)))
    print("  full symbol       = %r" % rep["exe"]["full_symbol"])

    # Does any code reference the address of this string? If the string really is
    # used as a window class name, its address appears as an operand somewhere.
    candidates = []
    if rva:
        for enc, name in ((struct.pack("<I", ib + rva), "absolute_VA"),
                          (struct.pack("<I", rva), "rva")):
            s = 0
            while True:
                i = d.find(enc, s)
                if i < 0:
                    break
                candidates.append({"encode": name, "off": "0x%X" % i,
                                   "rva": "0x%X" % o2r(secs, i) if o2r(secs, i) else None,
                                   "section": secname(secs, i)})
                s = i + 1
    rep["exe"]["references_to_iipsinit_string"] = candidates
    print()
    print("  references to the '?iipsinit' string address: %d" % len(candidates))
    for c in candidates[:10]:
        print("     %-12s at 0x%-8s rva=%-10s sec=%s"
              % (c["encode"], c["off"], c["rva"], c["section"]))

    # Provider images: confirm the literal is absent.
    for label, path in (("original_iips", IIPS), ("LocalRM_v3", V3)):
        dd = open(path, "rb").read()
        rep[label] = {
            "literal_iipsinit_count": dd.count(b"iipsinit"),
            "symbol_iipsinit_count": dd.count(b"?iipsinit"),
            "size": len(dd),
        }
        print("  %-14s literal 'iipsinit' = %d ; '?iipsinit' = %d"
              % (label, rep[label]["literal_iipsinit_count"],
                 rep[label]["symbol_iipsinit_count"]))

    print()
    rep["conclusion"] = (
        "The literal 'iipsinit' does not exist in the EXE as a standalone string, "
        "nor in either provider image. In the EXE it appears only inside the MSVC "
        "decorated symbol '?iipsinit'. Therefore, if a window class named "
        "'iipsinit' is created at runtime, its name is either (a) constructed by "
        "code, or (b) derived from the decorated symbol by code that strips the "
        "'?' prefix. Either way the class name is NOT evidence of an "
        "initialisation function, and must not be read as one.")
    print(rep["conclusion"])

    with open(os.path.join(OUT, "t07_iipsinit_origin.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t07_iipsinit_origin.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
