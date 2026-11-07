"""EB-003 Agent 05b - what is codoMP_client_shipRetailBase.dll ordinal 1?

The EXE imports exactly one function, by ordinal, from Base.dll. If Base.dll's
ordinal 1 is a conventional entry (e.g. IW-style "HostApp" / "main"-like export),
that confirms the EXE is a thin shim and Base.dll is the engine host that does the
LoadLibrary/GetProcAddress dance. Reported from bytes only.
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
        ch = struct.unpack_from("<I", d, o + 36)[0]
        out.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs, "ch": ch})
    return pe, magic, out


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def cstr(d, off, n=128):
    e = d.find(b"\0", off, off + n)
    return d[off:e if e >= 0 else off + n].decode("latin1")


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")
    d = open(path, "rb").read()
    pe, magic, secs = sections(d)

    print("=== Base.dll PE header ===")
    print("  size            = %d" % len(d))
    print("  machine         = 0x%04X" % struct.unpack_from("<H", d, pe + 4)[0])
    print("  characteristics = 0x%04X (%s)"
          % (struct.unpack_from("<H", d, pe + 22)[0],
             "DLL" if struct.unpack_from("<H", d, pe + 22)[0] & 0x2000 else "EXE"))
    print("  entrypoint RVA  = 0x%X" % struct.unpack_from("<I", d, pe + 24 + 16)[0])
    print("  image base      = 0x%X" % struct.unpack_from("<I", d, pe + 24 + 28)[0])
    print("  size of image   = 0x%X" % struct.unpack_from("<I", d, pe + 24 + 56)[0])
    print("  sections        = %s" % ", ".join(s["name"] for s in secs))

    # Export directory
    exp_rva = struct.unpack_from("<I", d, pe + 24 + 96)[0]
    exp_sz = struct.unpack_from("<I", d, pe + 24 + 96 + 4)[0]
    print("\n=== Base.dll exports (dir RVA 0x%X size %d) ===" % (exp_rva, exp_sz))
    res = {"entrypoint_rva": struct.unpack_from("<I", d, pe + 24 + 16)[0],
           "image_base": struct.unpack_from("<I", d, pe + 24 + 28)[0],
           "export_dir_rva": exp_rva, "exports": []}
    if exp_rva:
        off = r2o(secs, exp_rva)
        if off is not None:
            name_rva, base, nfn, nn = struct.unpack_from("<IIII", d, off + 12)
            aof, aon, aoo = struct.unpack_from("<III", d, off + 28)
            no = r2o(secs, name_rva)
            dll = cstr(d, no, 64) if no is not None else "?"
            print("  dll name  = %s" % dll)
            print("  Base=%d  nfunc=%d  nnames=%d" % (base, nfn, nn))
            res.update({"dll_name": dll, "base": base, "nfunc": nfn, "nnames": nn})
            fo = r2o(secs, aof)
            for k in range(min(nfn, 40)):
                fr = struct.unpack_from("<I", d, fo + k * 4)[0] if fo is not None else 0
                nm = None
                if nn:
                    for i in range(nn):
                        ov = struct.unpack_from("<H", d, r2o(secs, aoo) + i * 2)[0]
                        if ov == k:
                            nr = struct.unpack_from("<I", d, r2o(secs, aon) + i * 4)[0]
                            nm = cstr(d, r2o(secs, nr), 128)
                            break
                res["exports"].append({"ordinal": k + base, "name": nm, "rva": fr})
                print("    ord %-3d RVA 0x%-8X %s" % (k + base, fr, nm or ""))

    # The EXE's ordinal-1 target
    print("\n=== EXE import target ===")
    print("  codoMP_client_shipRetail.exe imports codoMP_client_shipRetailBase.dll #1")
    trg = next((e for e in res["exports"] if e["ordinal"] == 1), None)
    if trg:
        print("  -> Base.dll ordinal 1 = RVA 0x%X  name=%s"
              % (trg["rva"], trg["name"] or "(unnamed)"))
        res["exe_target"] = trg

    with open(os.path.join(OUT, "a05b_exe_ordinal1.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a05b_exe_ordinal1.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
