"""RESTORE-ENGINE-BRIDGE-003 / Agent 02 - who imports which iips exports?

Read-only static analysis of the two consumers that matter:
  * codoMP_client_shipRetail.exe
  * codoMP_client_shipRetailBase.dll

Determines by name and by ordinal whether either actually imports
GetResourceManagerII, and if so by which mechanism. Ordinal-only imports are the
trap here: an ordinal import binds to whatever sits at that index in whichever
DLL happens to be loaded, and the two providers have different ordinal layouts.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore003", "evidence")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    so = pe + 24 + (224 if magic == 0x10B else 240)
    out = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        out.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, magic, out


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def cstr(d, off):
    e = d.index(b"\0", off)
    return d[off:e].decode("latin1")


def imports(d, secs, pe, magic):
    opt = pe + 24
    if magic != 0x10B:
        return []
    imp_rva, imp_size = struct.unpack_from("<II", d, opt + 96 + 8)
    if imp_rva == 0:
        return []
    res = []
    off = r2o(secs, imp_rva)
    if off is None:
        return []
    i = 0
    while True:
        o = off + i * 20
        if o + 20 > len(d):
            break
        oft, ts, fc, namerva, fta = struct.unpack_from("<IIIII", d, o)
        if namerva == 0 and oft == 0 and fta == 0:
            break
        dll = cstr(d, r2o(secs, namerva)) if r2o(secs, namerva) is not None else "?"
        entries = []
        lookup = oft if oft else fta
        lo = r2o(secs, lookup)
        if lo is not None:
            j = 0
            while j < 4096:
                p = lo + j * 4
                if p + 4 > len(d):
                    break
                v = struct.unpack_from("<I", d, p)[0]
                if v == 0:
                    break
                if v & 0x80000000:
                    entries.append({"ordinal": v & 0xFFFF, "name": None})
                else:
                    no = r2o(secs, v)
                    hno = no + 2 if no is not None else None
                    nm = None
                    if hno is not None and hno < len(d):
                        try:
                            nm = cstr(d, hno)
                        except Exception:
                            nm = None
                    entries.append({"ordinal": None, "name": nm})
                j += 1
        res.append({"dll": dll, "entries": entries,
                    "iat_rva": fta, "oft_rva": oft})
        i += 1
    return res


def exports_of(path):
    d = open(path, "rb").read()
    pe, magic, secs = sections(d)
    opt = pe + 24
    exp_rva = struct.unpack_from("<I", d, opt + 96)[0]
    off = r2o(secs, exp_rva)
    res = {"path": path, "size": len(d)}
    if off is None:
        res["error"] = "no export dir"
        return res
    # The directory may be declared a few bytes off; try delta 0 then -4.
    for delta in (0, -4, -2, -8):
        o = off + delta
        try:
            name_rva, base, nfn, nn = struct.unpack_from("<IIII", d, o + 12)
            aof, aon, aoo = struct.unpack_from("<III", d, o + 28)
            if not (0 < nn <= 64 and 0 < nfn <= 64):
                continue
            no = r2o(secs, name_rva)
            if no is None:
                continue
            dll = cstr(d, no)
            if ".dll" not in dll.lower():
                continue
            ex = []
            for i in range(nn):
                nr = struct.unpack_from("<I", d, r2o(secs, aon) + i * 4)[0]
                ov = struct.unpack_from("<H", d, r2o(secs, aoo) + i * 2)[0]
                fr = struct.unpack_from("<I", d, r2o(secs, aof) + ov * 4)[0]
                ex.append({"name": cstr(d, r2o(secs, nr)),
                           "ordinal": ov + base, "func_rva": fr})
            res.update({"delta": delta, "dll_name": dll, "base": base,
                        "nfunc": nfn, "nnames": nn, "exports": ex})
            return res
        except Exception:
            continue
    res["error"] = "unparsed"
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}

    for label, rel in [
        ("exe", "codoMP_client_shipRetail.exe"),
        ("base", "codoMP_client_shipRetailBase.dll"),
    ]:
        path = os.path.join(GAME, rel)
        d = open(path, "rb").read()
        pe, magic, secs = sections(d)
        imps = imports(d, secs, pe, magic)
        rep[label] = {
            "path": rel,
            "size": len(d),
            "import_dll_count": len(imps),
            "iips_imports": [],
            "total_named_imports": sum(1 for i in imps for e in i["entries"] if e["name"]),
            "total_ordinal_imports": sum(1 for i in imps for e in i["entries"] if e["name"] is None),
        }
        for i in imps:
            if "iips" in i["dll"].lower():
                rep[label]["iips_imports"].append(i)
        # any DLL importing the RM names at all
        rep[label]["all_dlls"] = [i["dll"] for i in imps]

        # Is GetResourceManagerII imported anywhere?
        hits = []
        for i in imps:
            for e in i["entries"]:
                if e["name"] and "ResourceManager" in e["name"]:
                    hits.append({"dll": i["dll"], "name": e["name"],
                                 "ordinal": e["ordinal"], "iat_rva": i["iat_rva"]})
        rep[label]["resourcemanager_imports"] = hits

    rep["providers"] = {
        "original_iips": exports_of(os.path.join(GAME, "IIPS", "iips.dll")),
        "localrm_v3": exports_of(os.path.join(ROOT, "LocalRM_v3.dll")),
    }

    with open(os.path.join(OUT, "a02_import_binding.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    print("=== EB-003 Agent 02: import binding ===")
    for label in ("exe", "base"):
        r = rep[label]
        print("\n%s  (%s, %d bytes)" % (label, r["path"], r["size"]))
        print("  import DLLs: %d ; named imports: %d ; ordinal imports: %d"
              % (r["import_dll_count"], r["total_named_imports"], r["total_ordinal_imports"]))
        if r["iips_imports"]:
            for i in r["iips_imports"]:
                print("  imports %s  (IAT RVA 0x%X)" % (i["dll"], i["iat_rva"]))
                for e in i["entries"]:
                    print("      name=%-30s ordinal=%s" % (e["name"], e["ordinal"]))
        else:
            print("  does NOT import iips.dll")
        if r["resourcemanager_imports"]:
            for h in r["resourcemanager_imports"]:
                print("  ResourceManager import: %s!%s (ord %s)" % (h["dll"], h["name"], h["ordinal"]))

    print("\n--- provider export layouts ---")
    for k, v in rep["providers"].items():
        print("  %s: %s" % (k, v.get("dll_name", v.get("error"))))
        for e in v.get("exports", []):
            print("      %-30s ord=%d RVA=0x%X" % (e["name"], e["ordinal"], e["func_rva"]))
    print("\nwrote %s" % os.path.join(OUT, "a02_import_binding.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
