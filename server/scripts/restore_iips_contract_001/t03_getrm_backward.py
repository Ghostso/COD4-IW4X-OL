"""RESTORE-IIPS-CONTRACT-001 / Task 01 - backward analysis of GetResourceManagerII.

Static analysis of the ORIGINAL iips.dll (read-only).

Two distinct questions, deliberately kept apart:

  (1) INTRA-DLL backward analysis: which code inside iips.dll references the
      GetResourceManagerII body / the singleton guard? This reveals the DLL's own
      initialisation prerequisites (guard transitions, lazy construction, etc.).

  (2) EXTERNAL caller analysis: the Engine resolves GetResourceManagerII by NAME
      via GetProcAddress (established in RESTORE-ENGINE-BRIDGE-003), so there is no
      import-table edge to follow into the Engine. What CAN be recovered is every
      in-image reference to the export and to the guard variables it depends on.

The iips.dll image is small (0x55000) and fully statically available, so this is
done exhaustively rather than sampled.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")

GRM_RVA = 0x1C80          # GetResourceManagerII
REL_RVA = 0x1C60          # ReleaseResourceManagerII
GRM_I_RVA = 0x1BC0        # GetResourceManager
CTOR_RVA = 0x11F20        # ResourceManager ctor (LOCALRM-006)
OPERATOR_NEW_RVA = 0x2BE34

GUARD_RVA = 0x4EB6C       # singleton guard dword
SLOT_RVA = 0x4EB68        # singleton slot


def load(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    image_base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    so = pe + 24 + (224 if magic == 0x10B else 240)
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        ch = struct.unpack_from("<I", d, o + 36)[0]
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp,
                     "rsize": rs, "ch": ch})
    return d, pe, image_base, secs


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def o2r(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["va"] + (off - s["raw"])
    return None


def sec_of(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            return s["name"]
    return None


def reloc_set(d, secs, rel_rva, rel_size):
    relocs = {}
    off = r2o(secs, rel_rva)
    if off is None:
        return relocs
    end = min(off + rel_size, len(d))
    p = off
    while p + 8 <= end:
        page, bsz = struct.unpack_from("<II", d, p)
        if bsz < 8:
            break
        if p + bsz > end:
            bsz = end - p
            if bsz < 8:
                break
        for k in range((bsz - 8) // 2):
            q = p + 8 + k * 2
            if q + 2 > end:
                break
            w = struct.unpack_from("<H", d, q)[0]
            relocs[page + (w & 0xFFF)] = w >> 12
        p += bsz
    return relocs


def find_refs(d, secs, target_rva, relocs):
    """Find references to target_rva in the encodings that matter on x86:
    absolute/RVA imm32 (data or `mov reg,imm32`) and rel32 call/jmp."""
    hits = []
    n = len(d)
    needle = struct.pack("<I", target_rva)
    s = 0
    while True:
        i = d.find(needle, s)
        if i < 0:
            break
        rva_here = o2r(secs, i)
        if rva_here is not None:
            # classify: does a 0x68/0xB8-ish opcode start 1-2 bytes earlier?
            op = d[i - 1] if i > 0 else 0
            hits.append({"at_rva": "0x%X" % rva_here, "kind": "imm32",
                         "sec": sec_of(secs, rva_here),
                         "relocated": rva_here in relocs,
                         "opcode_before": "0x%02X" % op})
        s = i + 1
    for i in range(n - 5):
        op = d[i]
        if op not in (0xE8, 0xE9):
            continue
        src_rva = o2r(secs, i)
        if src_rva is None:
            continue
        disp = struct.unpack_from("<i", d, i + 1)[0]
        if src_rva + 5 + disp == target_rva:
            hits.append({"at_rva": "0x%X" % src_rva,
                         "kind": "rel32_call" if op == 0xE8 else "rel32_jmp",
                         "sec": sec_of(secs, src_rva), "relocated": False})
    return hits


def main():
    os.makedirs(OUT, exist_ok=True)
    d, pe, image_base, secs = load(IIPS)
    print("=== Task 01: backward analysis of GetResourceManagerII ===")
    print("  image base = 0x%08X   size = %d" % (image_base, len(d)))

    rel_rva, rel_size = struct.unpack_from("<II", d, pe + 24 + 96 + 40)
    relocs = reloc_set(d, secs, rel_rva, rel_size)
    print("  relocations = %d" % len(relocs))
    print()

    targets = {
        "GetResourceManagerII": GRM_RVA,
        "ReleaseResourceManagerII": REL_RVA,
        "GetResourceManager": GRM_I_RVA,
        "ResourceManager_ctor": CTOR_RVA,
        "operator_new": OPERATOR_NEW_RVA,
        "singleton_guard_0x4EB6C": GUARD_RVA,
        "singleton_slot_0x4EB68": SLOT_RVA,
    }
    rep = {"image_base": "0x%X" % image_base,
           "size": len(d), "references": {}}
    for label, rva in targets.items():
        refs = find_refs(d, secs, rva, relocs)
        rep["references"][label] = {"target_rva": "0x%X" % rva,
                                    "ref_count": len(refs), "refs": refs}
        print("  %-28s RVA 0x%-6X refs=%d" % (label, rva, len(refs)))
        for h in refs[:14]:
            print("       at %-10s %-12s sec=%-7s relocated=%s"
                  % (h["at_rva"], h["kind"], h["sec"], h["relocated"]))
        if len(refs) > 14:
            print("       ... %d more" % (len(refs) - 14))

    print()
    print("  LIMIT / HONEST STATEMENT")
    print("    A static caller CHAIN reaching the GetResourceManagerII export")
    print("    cannot be recovered from iips.dll alone: the callers live outside")
    print("    this image and the Engine reaches the export by NAME through")
    print("    GetProcAddress (RESTORE-ENGINE-BRIDGE-003), so no import edge")
    print("    exists to follow.")
    print("    STATIC_CHAIN_BLOCKED_AT_EXTERNAL_BOUNDARY")
    rep["static_chain_status"] = "STATIC_CHAIN_BLOCKED_AT_EXTERNAL_BOUNDARY"
    rep["static_chain_note"] = (
        "Callers of the GetResourceManagerII export are external to iips.dll and "
        "reached by name (GetProcAddress). No in-image caller chain exists to "
        "recover, so none is fabricated.")

    with open(os.path.join(OUT, "t03_getrm_backward.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t03_getrm_backward.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
