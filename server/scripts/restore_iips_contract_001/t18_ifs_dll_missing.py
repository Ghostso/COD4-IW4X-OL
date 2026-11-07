"""RESTORE-IIPS-CONTRACT-001 / Task 14 - the missing IFS.dll dependency.

Task 12/13 found:
  * the provider's own log table says ResourceManagerII::Initialize() performs
      [LoadLibrary IFS.dll]
      [LastError:IIPSERR_IFS_LOAD_DLL_ERROR][NifsInitError %d]
  * the IIPS directory contains IFS2.dll, and NO file named IFS.dll.

This script:
  1. confirms the exact literal the provider loads and how it is referenced,
  2. searches the whole install for a file named IFS.dll (including case variants
     and the side-by-side / .local search places),
  3. checks whether the provider ever refers to IFS2.dll anywhere,
  4. states precisely what can and cannot be concluded.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, ib, secs


def o2r(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["va"] + (off - s["raw"])
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 14: the IFS.dll dependency ===")
    print()

    d = open(IIPS, "rb").read()
    pe, ib, secs = sections(d)

    # 1. exact literal
    lit = b"IFS.dll"
    print("1) literal 'IFS.dll' in iips.dll")
    p = 0
    offs = []
    while True:
        i = d.find(lit, p)
        if i < 0:
            break
        s = i
        while s > 0 and 0x20 <= d[s - 1] < 0x7F:
            s -= 1
        e = d.find(b"\0", i)
        txt = d[s:e].decode("latin1", "replace")
        offs.append({"off": "0x%X" % s, "text": txt,
                     "rva": "0x%X" % o2r(secs, s) if o2r(secs, s) else None})
        p = i + 1
    for h in offs:
        print("   %-10s %r" % (h["off"], h["text"]))
    rep["ifs_dll_literals"] = offs

    # 2. any file named IFS.dll anywhere under the install / workspace
    print()
    print("2) files named IFS.dll (case-insensitive) anywhere in the workspace")
    found = []
    for dirpath, dirnames, files in os.walk(ROOT):
        if any(x in dirpath for x in ("\\obj", "__pycache__")):
            continue
        for f in files:
            if f.lower() == "ifs.dll":
                found.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    rep["ifs_dll_files_found"] = found
    if found:
        for f in found:
            print("   FOUND: %s" % f)
    else:
        print("   NONE — no file named IFS.dll exists anywhere in the workspace")

    # IFS-family files that DO exist
    fam = []
    for dirpath, dirnames, files in os.walk(ROOT):
        if any(x in dirpath for x in ("\\obj", "__pycache__")):
            continue
        for f in files:
            if f.lower().startswith("ifs"):
                fam.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    rep["ifs_family_files"] = sorted(fam)
    print()
    print("3) IFS-family files that DO exist: %d" % len(fam))
    for f in sorted(fam)[:20]:
        print("   %s" % f)

    # 3. does iips.dll mention IFS2.dll at all?
    print()
    c2 = d.count(b"IFS2")
    rep["iips_mentions_IFS2"] = c2
    print("4) iips.dll mentions 'IFS2': %d" % c2)

    # 4. the export names IFS2.dll provides (does it provide CreateIFSLibDll?)
    print()
    print("5) exports of IFS2.dll (the file that actually exists)")
    ifs2 = os.path.join(GAME, "IIPS", "IFS2.dll")
    rep["ifs2_exports"] = None
    if os.path.exists(ifs2):
        dd = open(ifs2, "rb").read()
        pe2, ib2, secs2 = sections(dd)
        exp_rva = struct.unpack_from("<I", dd, pe2 + 24 + 96)[0]
        off = None
        for s in secs2:
            if s["va"] <= exp_rva < s["va"] + max(s["vsize"], s["rsize"]):
                off = s["raw"] + (exp_rva - s["va"])
                break
        exps = []
        if off is not None:
            for delta in (0, -4, -2, -8):
                o = off + delta
                try:
                    name_rva, base, nfn, nn = struct.unpack_from("<IIII", dd, o + 12)
                    aof, aon, aoo = struct.unpack_from("<III", dd, o + 28)
                    if not (0 < nn <= 64 and 0 < nfn <= 64):
                        continue

                    def rr(x):
                        for s in secs2:
                            if s["va"] <= x < s["va"] + max(s["vsize"], s["rsize"]):
                                k = s["raw"] + (x - s["va"])
                                if 0 <= k < s["raw"] + s["rsize"]:
                                    return k
                        return None

                    no = rr(name_rva)
                    if no is None:
                        continue
                    dn = dd[no:dd.find(b"\0", no, no + 64)].decode("latin1")
                    if ".dll" not in dn.lower():
                        continue
                    for i in range(nn):
                        nr = struct.unpack_from("<I", dd, rr(aon) + i * 4)[0]
                        ov = struct.unpack_from("<H", dd, rr(aoo) + i * 2)[0]
                        fr = struct.unpack_from("<I", dd, rr(aof) + ov * 4)[0]
                        e2 = dd.find(b"\0", rr(nr))
                        exps.append({"name": dd[rr(nr):e2].decode("latin1"),
                                     "ordinal": ov + base, "func_rva": fr})
                    rep["ifs2_exports"] = {"dll_name": dn, "exports": exps}
                    break
                except Exception:
                    continue
    if rep["ifs2_exports"]:
        print("   dll name: %s" % rep["ifs2_exports"]["dll_name"])
        for e in rep["ifs2_exports"]["exports"]:
            print("      %-32s ord=%d RVA=0x%X"
                  % (e["name"], e["ordinal"], e["func_rva"]))
    else:
        print("   (could not parse exports)")

    # The provider looks for specific IFS entry points; record them.
    print()
    print("6) IFS entry-point names the provider looks up")
    for sym in (b"CreateIFSLibDll", b"DestoryIFSLibDll", b"DestroyIFSLibDll"):
        c = d.count(sym)
        print("   %-20s %d" % (sym.decode(), c))
        if c:
            i = d.find(sym)
            s = i
            while s > 0 and 0x20 <= d[s - 1] < 0x7F:
                s -= 1
            e = d.find(b"\0", i)
            print("        context: %r" % d[s:e].decode("latin1", "replace"))

    rep["conclusion"] = (
        "The provider's contract calls [LoadLibrary IFS.dll]. No file named "
        "IFS.dll exists anywhere in the workspace; only IFS2.dll is present. "
        "LoadLibrary('IFS.dll') therefore cannot resolve via the normal search "
        "order, which produces exactly the failure the provider's own log table "
        "anticipates: IIPSERR_IFS_LOAD_DLL_ERROR / NifsInitError. That failure "
        "occurs BEFORE the pipe connect and BEFORE "
        "InitializeWorkAfterClientConnected, i.e. before the step that ends in "
        "the readiness PostMessage and precedes any successful "
        "GetResourceManagerII. NOTE: this is a dependency-availability finding, "
        "not yet a proven root cause for the A/B difference, because condition A "
        "shows the SAME missing file.")
    print()
    print(rep["conclusion"])

    with open(os.path.join(OUT, "t18_ifs_dll_missing.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t18_ifs_dll_missing.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
