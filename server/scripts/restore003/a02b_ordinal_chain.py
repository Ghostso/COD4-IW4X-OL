"""EB-003 Agent 02b - resolve the ordinal-import chain that reaches iips.dll.

The EXE's sole import is an ordinal import; the export-parsing in a02 reported
only named imports for Base.dll. This script:

  1. prints the EXE's ordinal import verbatim (DLL + ordinal),
  2. scans every module in the install for a *named or ordinal* reference to
     iips.dll's exports (importable evidence of the real consumer),
  3. resolves which ordinal actually carries GetResourceManagerII in each
     provider, to show the ordinal-layout mismatch concretely.
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


def cstr(d, off, maxlen=256):
    e = d.find(b"\0", off, off + maxlen)
    if e < 0:
        e = off + maxlen
    return d[off:e].decode("latin1")


def import_descriptors(path):
    """Return [{dll, entries:[{name,ordinal,iat_rva}]}] for a 32-bit PE."""
    d = open(path, "rb").read()
    pe, magic, secs = sections(d)
    if magic != 0x10B:
        return d, []
    imp_rva, imp_size = struct.unpack_from("<II", d, pe + 24 + 96 + 8)
    if imp_rva == 0:
        return d, []
    off = r2o(secs, imp_rva)
    if off is None:
        return d, []
    out = []
    i = 0
    while True:
        o = off + i * 20
        if o + 20 > len(d):
            break
        oft, ts, fc, namerva, fta = struct.unpack_from("<IIIII", d, o)
        if namerva == 0 and oft == 0 and fta == 0:
            break
        no = r2o(secs, namerva)
        dll = cstr(d, no) if no is not None else "?"
        entries = []
        lookup = oft if oft else fta
        lo = r2o(secs, lookup)
        if lo is not None:
            j = 0
            while j < 8192:
                p = lo + j * 4
                if p + 4 > len(d):
                    break
                v = struct.unpack_from("<I", d, p)[0]
                if v == 0:
                    break
                if v & 0x80000000:
                    entries.append({"name": None, "ordinal": v & 0xFFFF,
                                    "iat_slot_rva": fta + j * 4})
                else:
                    hno = r2o(secs, v)
                    nm = None
                    if hno is not None and hno + 2 < len(d):
                        try:
                            nm = cstr(d, hno + 2)
                        except Exception:
                            nm = None
                    entries.append({"name": nm, "ordinal": None,
                                    "iat_slot_rva": fta + j * 4})
                j += 1
        out.append({"dll": dll, "entries": entries, "iat_rva": fta, "oft_rva": oft})
        i += 1
    return d, out


def exports_of(path):
    d = open(path, "rb").read()
    pe, magic, secs = sections(d)
    exp_rva = struct.unpack_from("<I", d, pe + 24 + 96)[0]
    off = r2o(secs, exp_rva)
    res = {"file": os.path.basename(path), "size": len(d),
           "address_of_functions": [], "named": []}
    for delta in (0, -4, -2, -8, 4, 8):
        o = off + delta
        if o is None or o < 0 or o + 40 > len(d):
            continue
        try:
            name_rva, base, nfn, nn = struct.unpack_from("<IIII", d, o + 12)
            aof, aon, aoo = struct.unpack_from("<III", d, o + 28)
            if not (0 < nn <= 64 and 0 < nfn <= 64):
                continue
            no = r2o(secs, name_rva)
            if no is None:
                continue
            dll = cstr(d, no, 64)
            if ".dll" not in dll.lower():
                continue
            res["dll_name"] = dll
            res["dir_delta"] = delta
            res["base"] = base
            res["number_of_functions"] = nfn
            res["number_of_names"] = nn
            fo = r2o(secs, aof)
            for k in range(nfn):
                fr = struct.unpack_from("<I", d, fo + k * 4)[0]
                res["address_of_functions"].append(
                    {"ordinal": k + base, "func_rva": fr})
            for i in range(nn):
                nr = struct.unpack_from("<I", d, r2o(secs, aon) + i * 4)[0]
                ov = struct.unpack_from("<H", d, r2o(secs, aoo) + i * 2)[0]
                fr = struct.unpack_from("<I", d, fo + ov * 4)[0]
                res["named"].append({"name": cstr(d, r2o(secs, nr), 64),
                                     "ordinal_index": ov, "ordinal": ov + base,
                                     "func_rva": fr})
            return res
        except Exception:
            continue
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}

    exe = os.path.join(GAME, "codoMP_client_shipRetail.exe")
    d, imps = import_descriptors(exe)
    rep["exe_imports"] = imps
    print("=== EXE imports (verbatim) ===")
    for i in imps:
        print("  DLL: %s  (IAT RVA 0x%X, %d entries)" % (i["dll"], i["iat_rva"], len(i["entries"])))
        for e in i["entries"]:
            print("      name=%-30s ordinal=%s iatSlot=0x%X"
                  % (e["name"], e["ordinal"], e["iat_slot_rva"]))

    # Who references iips at all (by name in data or by import)?
    print("\n=== scanning install for iips.dll references ===")
    hits = []
    for fn in sorted(os.listdir(GAME)):
        if not fn.lower().endswith((".dll", ".exe")):
            continue
        p = os.path.join(GAME, fn)
        try:
            dd, imps2 = import_descriptors(p)
        except Exception:
            continue
        for i in imps2:
            if i["dll"].lower().startswith("iips"):
                hits.append({"module": fn, "dll": i["dll"],
                             "imports": i["entries"]})
        # also raw string presence
        if b"iips.dll" in dd:
            hits.append({"module": fn, "dll": "iips.dll", "raw_string": True})
    for h in hits:
        print("  %s" % json.dumps(h))
    rep["iips_references"] = hits

    print("\n=== ordinal layout comparison ===")
    rep["providers"] = {
        "original_iips": exports_of(os.path.join(GAME, "IIPS", "iips.dll")),
        "localrm_v3": exports_of(os.path.join(ROOT, "LocalRM_v3.dll")),
    }
    for k, v in rep["providers"].items():
        print("  %s (%s, %d bytes)" % (k, v.get("dll_name"), v["size"]))
        for e in v["address_of_functions"]:
            nm = next((x["name"] for x in v["named"] if x["ordinal"] == e["ordinal"]), None)
            print("      ordinal %-3d -> RVA 0x%-6X %s"
                  % (e["ordinal"], e["func_rva"], ("(" + nm + ")") if nm else ""))

    with open(os.path.join(OUT, "a02b_ordinal_chain.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a02b_ordinal_chain.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
