"""RESTORE-ENGINE-BRIDGE-003 / Agent 01 - static recon of the A/B artifacts.

Read-only. Establishes, from bytes on disk only:
  * identity (path, size, mtime, SHA256) of every artifact the round depends on
  * original iips.dll export ABI (GetResourceManagerII / ReleaseResourceManagerII)
  * LocalRM_v3.dll .localrm layout, exports, guard/instance, 48-slot vtable
  * one real defect found in LocalRM_v3.dll's export directory (recorded, not fixed)

No process is started here. Nothing on disk is written outside restore003/.
"""
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore003", "evidence")

IMPORTANT = [
    ("codoMP_client_shipRetail.exe", os.path.join(GAME, "codoMP_client_shipRetail.exe")),
    ("iips.dll (ORIGINAL, condition A provider)", os.path.join(GAME, "IIPS", "iips.dll")),
    ("codoMP_client_shipRetailBase.dll", os.path.join(GAME, "codoMP_client_shipRetailBase.dll")),
    ("BugTrace.dll", os.path.join(GAME, "BugTrace.dll")),
    ("TenProxy.dll", os.path.join(GAME, "TenProxy.dll")),
    ("LocalRM_v3.dll (condition B provider)", os.path.join(ROOT, "LocalRM_v3.dll")),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


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


def rva_to_off(secs, rva):
    """Map an RVA to a file offset using the section that *contains* it.

    The extent used for containment is max(VirtualSize, SizeOfRawData), but the
    returned offset is only valid when it also lands inside the section's raw
    data; otherwise None is returned. This matters for these artifacts because
    their virtual size (0x55000) exceeds their file size, so an RVA can be
    'contained' yet point past EOF.
    """
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if off < s["raw"] or off >= s["raw"] + s["rsize"]:
                return None
            return off
    return None


def parse_exports(d, secs, export_dir_rva, note_expected_offset=None):
    """Parse IMAGE_EXPORT_DIRECTORY, tolerating a dir that starts N bytes early."""
    off = rva_to_off(secs, export_dir_rva)
    res = {"dir_rva": export_dir_rva, "dir_off": off, "candidates": []}
    if off is None:
        return res
    for delta in (0, -2, -4, -8, 8, 4):
        o = off + delta
        if o < 0 or o + 40 > len(d):
            continue
        name_rva, base, nfn, nn = struct.unpack_from("<IIII", d, o + 12)
        aof, aon, aoo = struct.unpack_from("<III", d, o + 28)
        cand = {"delta": delta, "name_rva": name_rva, "base": base,
                "nfunc": nfn, "nnames": nn, "aof": aof, "aon": aon, "aoo": aoo}
        ok = True
        try:
            if not (1 <= nfn <= 64 and 1 <= nn <= 64):
                ok = False
            no = rva_to_off(secs, name_rva)
            if no is None:
                ok = False
            else:
                e = d.index(b"\0", no)
                cand["dll_name"] = d[no:e].decode("latin1")
            names = []
            aon_off = rva_to_off(secs, aon)
            aoo_off = rva_to_off(secs, aoo)
            aof_off = rva_to_off(secs, aof)
            if aon_off is None or aoo_off is None or aof_off is None:
                ok = False
            for i in range(nn):
                if not ok:
                    break
                p, q = aon_off, aoo_off
                # AddressOfNames is a DWORD array; AddressOfNameOrdinals is a
                # WORD array (2-byte stride). Mixing the strides up silently
                # produces garbage ordinals, so each is bounds-checked with its
                # own element width.
                if p + i * 4 + 4 > len(d) or q + i * 2 + 2 > len(d):
                    ok = False
                    break
                nr = struct.unpack_from("<I", d, p + i * 4)[0]
                ordv = struct.unpack_from("<H", d, q + i * 2)[0]
                fo = aof_off
                if fo + ordv * 4 + 4 > len(d):
                    ok = False
                    break
                fr = struct.unpack_from("<I", d, fo + ordv * 4)[0]
                so = rva_to_off(secs, nr)
                if so is None:
                    ok = False
                    break
                e = d.index(b"\0", so)
                names.append({"name": d[so:e].decode("latin1"),
                              "ordinal": ordv + base, "func_rva": fr})
            cand["exports"] = names
        except Exception as ex:  # noqa: BLE001
            ok = False
            cand["error"] = repr(ex)
        cand["plausible"] = ok
        res["candidates"].append(cand)
    res["expected_off"] = note_expected_offset
    return res


def export_dir_selfcheck(d, secs, export_dir_rva):
    """Detect a misaligned export directory.

    A well-formed IMAGE_EXPORT_DIRECTORY begins exactly at the Data Directory's
    RVA. If the *first* 40 bytes at that RVA do not look like an export
    directory but the bytes a few bytes earlier do, the image is misaligned.
    We report where the structure actually starts rather than silently
    tolerating it.
    """
    off = rva_to_off(secs, export_dir_rva)
    out = {"declared_rva": export_dir_rva, "declared_off": off, "actual_start": None,
           "delta": None, "explanation": None}
    if off is None:
        return out

    def looks_like(o):
        if o < 0 or o + 40 > len(d):
            return None
        td, maj, minr, name_rva, base, nfn, nn = struct.unpack_from("<IIIIIII", d, o + 4)
        if name_rva == 0 and nfn == 0 and nn == 0:
            return None
        if not (0 < nn <= 64 and 0 < nfn <= 64):
            return None
        n = rva_to_off(secs, name_rva)
        if n is None or n + 4 > len(d):
            return None
        e = d.find(b"\0", n, n + 260)
        if e < 0:
            return None
        name = d[n:e]
        if not name or not all(0x20 <= c < 0x7F for c in name):
            return None
        # A DLL module name conventionally ends in ".dll" (optionally followed by
        # a version suffix). If it does not, this is not the export directory.
        if b".dll" not in name.lower():
            return None
        return {"name_rva": name_rva, "base": base, "nfunc": nfn, "nnames": nn,
                "dll_name": name.decode("latin1")}

    for delta in (0, -2, -4, -6, -8, -10, -12, -16, 2, 4, 8):
        r = looks_like(off + delta)
        if r:
            out["actual_start"] = off + delta
            out["delta"] = delta
            out["structure"] = r
            break
    if out["delta"] == 0:
        out["explanation"] = "export directory is correctly aligned"
    elif out["delta"] is not None:
        out["explanation"] = (
            "Data Directory EXPORT RVA points %d byte(s) too %s; the real "
            "IMAGE_EXPORT_DIRECTORY starts at file offset 0x%X (RVA 0x%X). "
            "The Windows loader tolerates this (both exports resolve), but the "
            "image is structurally misaligned." % (
                abs(out["delta"]), "late" if out["delta"] > 0 else "early",
                out["actual_start"], export_dir_rva + out["delta"]))
    else:
        out["explanation"] = "no plausible IMAGE_EXPORT_DIRECTORY found near declared RVA"
    return out


def disasm_exports_localrm(d):
    """Disassemble the two .localrm export bodies (hand-decoded, no disassembler)."""
    b = 0x55000
    grm = d[b + 0x000:b + 0x000 + 31]
    rel = d[b + 0x040:b + 0x040 + 20]
    stub = d[b + 0x0C0:b + 0x0C0 + 6]
    dtor = d[b + 0x080:b + 0x080 + 30]
    lazy = d[b + 0x0E0:b + 0x0E0 + 84]
    dllmain = d[b + 0x180:b + 0x180 + 6]
    return {
        "GetResourceManagerII_bytes": grm.hex(" ").upper(),
        "ReleaseResourceManagerII_bytes": rel.hex(" ").upper(),
        "shared_stub_bytes": stub.hex(" ").upper(),
        "deleting_destructor_bytes": dtor.hex(" ").upper(),
        "lazy_init_bytes": lazy.hex(" ").upper(),
        "DllMain_bytes": dllmain.hex(" ").upper(),
        "notes": {
            "GetResourceManagerII":
                "b8 00 52 05 10  mov eax,0x10055200 (&guard?) ; "
                "83 38 00        cmp dword [eax],0 ; "
                "74 08           je  lazy_init ; "
                "b8 04 52 05 10  mov eax,0x10055204 ; 8b 00 mov eax,[eax] ; c3 ret. "
                "So +0x200 reads as the 'instance slot' in this build.",
            "ReleaseResourceManagerII":
                "8b 4c 24 04 mov ecx,[esp+4] (arg1) ; 85 c9 test ecx,ecx ; "
                "74 0b je ret ; 8b 01 mov eax,[ecx] ; 8b 10 mov edx,[eax] ; "
                "68 01 00 00 00 push 1 ; ff d2 call edx ; c3 ret. "
                "=> __cdecl, NULL-safe, vtable[0](this,1).",
            "shared_stub": "b8 01 00 00 00 mov eax,1 ; c3 ret  (single shared stub)",
            "lazy_init":
                "68 10 04 00 00  push 0x410 ; ff 15 8c 32 03 10  call [0x1003328C] (operator new) ; "
                "stores 4 vptrs at +0x00/+0x04/+0x20/+0x44 (0x10055210/14/30/54) ; "
                "then writes instance into [0x10055204] and 1 into [0x10055200].",
            "DllMain": "b8 01 00 00 00 mov eax,1 ; c2 0c 00 ret 0x0C  (stdcall DllMain)",
        },
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {"agents": {}, "artifacts": []}

    for label, path in IMPORTANT:
        if not os.path.exists(path):
            rep["artifacts"].append({"label": label, "path": path, "status": "MISSING"})
            continue
        st = os.stat(path)
        rep["artifacts"].append({
            "label": label,
            "path": path,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "sha256": sha256(path),
            "status": "PRESENT",
        })

    # --- original iips.dll exports (condition A provider) ---
    ipath = os.path.join(GAME, "IIPS", "iips.dll")
    d = open(ipath, "rb").read()
    pe, magic, secs = sections(d)
    dirs = struct.unpack_from("<16I", d, pe + 24 + 96)
    ex = parse_exports(d, secs, dirs[0])
    best = next((c for c in ex["candidates"] if c.get("plausible")), None)
    rep["agents"]["A01_original_iips"] = {
        "path": ipath, "size": len(d), "machine": hex(struct.unpack_from("<H", d, pe + 4)[0]),
        "magic": hex(magic),
        "sections": secs,
        "export_dir": ex,
        "resolved": best,
        "GetResourceManagerII_rva": 0x1C80,
        "ReleaseResourceManagerII_rva": 0x1C60,
        "GetResourceManagerII_head": d[rva_to_off(secs, 0x1C80):rva_to_off(secs, 0x1C80) + 40].hex(" ").upper(),
        "ReleaseResourceManagerII_head": d[rva_to_off(secs, 0x1C60):rva_to_off(secs, 0x1C60) + 20].hex(" ").upper(),
    }

    # --- LocalRM_v3.dll (condition B provider) ---
    v3 = os.path.join(ROOT, "LocalRM_v3.dll")
    d3 = open(v3, "rb").read()
    pe3, magic3, secs3 = sections(d3)
    dirs3 = struct.unpack_from("<16I", d3, pe3 + 24 + 96)
    ex3 = parse_exports(d3, secs3, dirs3[0])
    best3 = next((c for c in ex3["candidates"] if c.get("plausible")), None)
    b = 0x55000

    def u32(o):
        return struct.unpack_from("<I", d3, b + o)[0]

    vtable = [u32(0x210 + i * 4) for i in range(48)]
    rep["agents"]["A02_localrm_v3"] = {
        "path": v3, "size": len(d3), "machine": hex(struct.unpack_from("<H", d3, pe3 + 4)[0]),
        "magic": hex(magic3),
        "entrypoint_rva": hex(struct.unpack_from("<I", d3, pe3 + 24 + 16)[0]),
        "sections": secs3,
        "export_dir": ex3,
        "export_dir_selfcheck": export_dir_selfcheck(d3, secs3, dirs3[0]),
        "resolved": best3,
        "export_dir_declared_rva": hex(dirs3[0]),
        "export_dir_actual_off": hex(rva_to_off(secs3, dirs3[0])),
        "localrm_layout": disasm_exports_localrm(d3),
        "guard_dword_offset_localrm_0x200": hex(u32(0x200)),
        "instance_dword_offset_localrm_0x204": hex(u32(0x204)),
        "vtable_localrm_0x210_48slots": ["0x%08X" % v for v in vtable],
        "vtable_distinct_targets": sorted(set("0x%08X" % v for v in vtable)),
        "slot0_target": "0x%08X" % vtable[0],
        "slots_1_to_47_share_stub": len(set(vtable[1:])) == 1,
    }

    with open(os.path.join(OUT, "a01_artifact_recon.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    print("=== RESTORE-ENGINE-BRIDGE-003 Agent 01: artifact recon ===")
    for a in rep["artifacts"]:
        if a["status"] != "PRESENT":
            print("  MISSING %s" % a["label"])
            continue
        print("  %-46s %10d  %s" % (a["label"], a["size"], a["sha256"][:16] + "..."))
    print()
    r = rep["agents"]["A01_original_iips"]
    print("original iips.dll  machine=%s magic=%s" % (r["machine"], r["magic"]))
    if r["resolved"]:
        for e in r["resolved"]["exports"]:
            print("   export %-28s ord=%d RVA=0x%X" % (e["name"], e["ordinal"], e["func_rva"]))
    print("   GetResourceManagerII@0x1C80 : %s" % r["GetResourceManagerII_head"])
    print("   ReleaseRMII@0x1C60          : %s" % r["ReleaseResourceManagerII_head"])
    print()
    v = rep["agents"]["A02_localrm_v3"]
    print("LocalRM_v3.dll     machine=%s magic=%s entry=0x%X" % (v["machine"], v["magic"], int(v["entrypoint_rva"], 16)))
    if v["resolved"]:
        for e in v["resolved"]["exports"]:
            print("   export %-28s ord=%d RVA=0x%X" % (e["name"], e["ordinal"], e["func_rva"]))
    print("   declared EXPORT dir RVA=%s -> file off %s" % (v["export_dir_declared_rva"], v["export_dir_actual_off"]))
    print("   vtable distinct targets: %s" % ", ".join(v["vtable_distinct_targets"]))
    print("   slots 1..47 share one stub: %s" % v["slots_1_to_47_share_stub"])
    print()
    print("wrote %s" % os.path.join(OUT, "a01_artifact_recon.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
