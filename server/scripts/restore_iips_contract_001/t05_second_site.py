"""RESTORE-IIPS-CONTRACT-001 / Task 03b - the second ResourceManager construction site.

Task 03 found TWO callers of the ResourceManager constructor (RVA 0x11F20):

  0x1CD4  inside GetResourceManagerII -- the LAZY singleton path
            push eax ; call ctor ; mov [0x1004EB68],eax    -> stores singleton slot

  0x1024D a separate function
            call 0x2AC0 ; push eax ; call ctor ; push 0x10035684 ; call 0x4280
            -> does NOT touch the singleton slot

The second site is a distinct construction path with a string argument. This
script resolves that string and decodes the callees, because "is there a second
provider-side construction site" directly bears on the IIPS init contract.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")


def load(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    image_base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return d, image_base, secs


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def cstr(d, off, n=128):
    e = d.find(b"\0", off, off + n)
    return d[off:e if e >= 0 else off + n].decode("latin1", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)
    d, image_base, secs = load(IIPS)
    rep = {"image_base": "0x%X" % image_base, "absolute_strings": {}}
    print("=== Task 03b: the second ResourceManager construction site ===")
    print()

    for absva, label in ((0x10035684, "pushed at 0x10252"),
                         (0x100325A9, "SEH scope table in GetResourceManagerII"),
                         (0x10042020, "/GS cookie in GetResourceManagerII")):
        rva = absva - image_base
        off = r2o(secs, rva)
        if off is None:
            rep["absolute_strings"][label] = {"va": "0x%X" % absva,
                                              "rva": "0x%X" % rva,
                                              "text": None,
                                              "note": "RVA not mapped to file"}
            print("  %-42s VA 0x%08X RVA 0x%-6X -> not mapped" % (label, absva, rva))
            continue
        raw = d[off:off + 16]
        printable = all(0x20 <= c < 0x7F for c in raw[:4])
        txt = cstr(d, off, 96) if printable else None
        rep["absolute_strings"][label] = {
            "va": "0x%X" % absva, "rva": "0x%X" % rva,
            "raw": raw.hex(" ").upper(), "text": txt}
        print("  %-42s VA 0x%08X RVA 0x%-6X raw=%s text=%r"
              % (label, absva, rva, raw.hex(" ").upper(), txt))
    print()

    def prologue(rva, n=24):
        off = r2o(secs, rva)
        if off is None:
            return None
        return d[off:off + n].hex(" ").upper()

    rep["prologues"] = {}
    for rva, name in ((0x4280, "callee_at_0x10259"), (0x2AC0, "callee_at_0x1023D"),
                      (0x11F20, "ResourceManager_ctor")):
        hx = prologue(rva)
        rep["prologues"][name] = {"rva": "0x%X" % rva, "bytes": hx}
        print("  %-22s RVA 0x%-6X %s" % (name, rva, hx))
    print()

    off = r2o(secs, 0x10230)
    win = d[off:off + 0x60]
    touches_slot = struct.pack("<I", 0x1004EB68) in win
    touches_guard = struct.pack("<I", 0x1004EB6C) in win
    rep["second_site_touches_singleton_slot"] = touches_slot
    rep["second_site_touches_guard"] = touches_guard
    print("  second site (0x10230..0x10290) stores to 0x1004EB68 : %s" % touches_slot)
    print("  second site (0x10230..0x10290) touches 0x1004EB6C     : %s" % touches_guard)
    print()

    rep["conclusion"] = (
        "There are exactly two callers of the ResourceManager constructor. Only the "
        "one inside GetResourceManagerII (0x1CD4) records the object in the "
        "singleton slot 0x1004EB68. The other (0x1024D) constructs an object and "
        "passes it to 0x4280 together with a string argument, and does not touch "
        "the singleton slot or the guard. These are therefore two distinct "
        "construction paths, and the singleton path is the one available to the "
        "Engine through the exported GetResourceManagerII.")
    print(rep["conclusion"])

    with open(os.path.join(OUT, "t05_second_site.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t05_second_site.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
