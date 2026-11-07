"""EB-003 Agent 05 - is Base.dll the real host that resolves iips?

The EXE's whole import table is one entry (Base.dll ordinal 1), and it imports no
LoadLibrary/GetProcAddress. So whatever loads "IIPS\\iips.dll" must be Base.dll
(or a module Base.dll pulls in). This resolves that chain from bytes.
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


def cstr(d, off, n=256):
    e = d.find(b"\0", off, off + n)
    return d[off:e if e >= 0 else off + n].decode("latin1")


def all_imports(path):
    d = open(path, "rb").read()
    pe, magic, secs = sections(d)
    imp_rva = struct.unpack_from("<I", d, pe + 24 + 96 + 8)[0]
    res = []
    if imp_rva == 0:
        return d, res, secs, pe
    off = r2o(secs, imp_rva)
    if off is None:
        return d, res, secs, pe
    i = 0
    while True:
        o = off + i * 20
        if o + 20 > len(d):
            break
        oft, ts, fc, nr, fta = struct.unpack_from("<IIIII", d, o)
        if nr == 0 and oft == 0 and fta == 0:
            break
        no = r2o(secs, nr)
        dll = cstr(d, no, 64) if no is not None else "?"
        names = []
        lookup = oft if oft else fta
        lo = r2o(secs, lookup)
        if lo is not None:
            j = 0
            while j < 20000:
                p = lo + j * 4
                if p + 4 > len(d):
                    break
                v = struct.unpack_from("<I", d, p)[0]
                if v == 0:
                    break
                if v & 0x80000000:
                    names.append("#%d" % (v & 0xFFFF))
                else:
                    h = r2o(secs, v)
                    if h is not None and h + 2 < len(d):
                        try:
                            names.append(cstr(d, h + 2))
                        except Exception:
                            names.append("?")
                j += 1
        res.append({"dll": dll, "names": names, "iat_rva": fta, "count": len(names)})
        i += 1
    return d, res, secs, pe


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}

    for label, rel in [
        ("base", "codoMP_client_shipRetailBase.dll"),
        ("exe", "codoMP_client_shipRetail.exe"),
    ]:
        d, imps, secs, pe = all_imports(os.path.join(GAME, rel))
        rep[label] = {"size": len(d), "sections": [s["name"] for s in secs],
                      "imported_dlls": [i["dll"] for i in imps],
                      "import_count": len(imps),
                      "total_imported_functions": sum(i["count"] for i in imps),
                      "has_loadlibrary": None,
                      "has_getprocaddress": None,
                      "container_strings": {}}
        flat = {}
        for i in imps:
            for n in i["names"]:
                flat.setdefault(n, []).append(i["dll"])
        rep[label]["has_loadlibrary"] = any(
            n in flat for n in ("LoadLibraryA", "LoadLibraryW", "LoadLibraryExA",
                                "LoadLibraryExW"))
        rep[label]["has_getprocaddress"] = "GetProcAddress" in flat
        rep[label]["loadlibrary_importers"] = {
            n: flat[n] for n in flat if n.startswith("LoadLibrary")}
        rep[label]["getprocaddress_importers"] = flat.get("GetProcAddress", [])
        # container-related strings
        for needle in (b"IIPS\\iips.dll", b"GetResourceManagerII",
                       b"ReleaseResourceManagerII", b"iips.dll"):
            rep[label]["container_strings"][needle.decode("latin1",
                "replace")] = d.count(needle)

    print("=== EB-003 Agent 05: host / resolution chain ===")
    for k in ("exe", "base"):
        r = rep[k]
        print("\n%s  %d bytes, %d sections" % (k, r["size"], len(r["sections"])))
        print("  imported DLLs (%d): %s" % (r["import_count"], ", ".join(r["imported_dlls"][:20])))
        print("  total imported functions: %d" % r["total_imported_functions"])
        print("  imports LoadLibrary*: %s   GetProcAddress: %s"
              % (r["has_loadlibrary"], r["has_getprocaddress"]))
        if r["getprocaddress_importers"]:
            print("  GetProcAddress imported from: %s" % ", ".join(r["getprocaddress_importers"]))
        if r["loadlibrary_importers"]:
            for n, v in sorted(r["loadlibrary_importers"].items()):
                print("  %s <- %s" % (n, ", ".join(v)))
        print("  strings: %s" % json.dumps(r["container_strings"]))

    with open(os.path.join(OUT, "a05_base_host.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a05_base_host.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
