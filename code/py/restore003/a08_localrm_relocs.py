"""EB-003 Agent 08 - does LocalRM_v3.dll relocate correctly away from its preferred base?

This matters because .localrm's stubs use ABSOLUTE immediates encoding the
preferred image base 0x10000000, e.g.

    GetResourceManagerII:  mov eax, 0x10055200        ; guard/instance slot
                           mov [edx+0x00], 0x10055210 ; vtable pointer
    lazy_init:             push 0x410
                           call dword ptr [0x1003328C] ; operator new (IAT)

If .localrm is not covered by base relocations, then when the module loads
somewhere other than 0x10000000 every one of those immediates is wrong by
(actualBase - 0x10000000). That is a concrete, falsifiable defect, and it would
explain a load-succeeds-but-call-faults behaviour.

Read-only.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "restore003", "evidence")


def parse(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    preferred = struct.unpack_from("<I", d, pe + 24 + 28)[0]
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
    rel_rva, rel_size = struct.unpack_from("<II", d, pe + 24 + 96 + 40)
    return d, pe, magic, preferred, secs, rel_rva, rel_size


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def relocs(d, secs, rel_rva, rel_size):
    """Yield every relocated RVA. Bounds-checked against both section and file."""
    out = []
    off = r2o(secs, rel_rva)
    if off is None:
        return out, 0, 0
    end = min(off + rel_size, len(d))
    p = off
    blocks = 0
    while p + 8 <= end:
        page, bsz = struct.unpack_from("<II", d, p)
        if bsz < 8:
            break
        if p + bsz > end:
            # truncated final block
            bsz = end - p
            if bsz < 8:
                break
        nent = (bsz - 8) // 2
        for k in range(nent):
            q = p + 8 + k * 2
            if q + 2 > end:
                break
            w = struct.unpack_from("<H", d, q)[0]
            out.append(page + (w & 0xFFF))
        blocks += 1
        p += bsz
    return out, blocks, len(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(ROOT, "LocalRM_v3.dll")
    d, pe, magic, preferred, secs, rel_rva, rel_size = parse(path)
    rl, nblocks, nent = relocs(d, secs, rel_rva, rel_size)

    print("=== EB-003 Agent 08: LocalRM_v3.dll base relocations ===")
    print("  file            = %s" % path)
    print("  preferred base  = 0x%08X" % preferred)
    print("  reloc dir       = RVA 0x%X size %d" % (rel_rva, rel_size))
    print("  reloc blocks    = %d ; entries = %d" % (nblocks, nent))

    sec_of = {}
    for s in secs:
        sec_of[s["name"]] = (s["va"], s["va"] + max(s["vsize"], s["rsize"]))
    counts = {}
    for v in rl:
        for nm, (a, b) in sec_of.items():
            if a <= v < b:
                counts[nm] = counts.get(nm, 0) + 1
                break
        else:
            counts["<unmapped>"] = counts.get("<unmapped>", 0) + 1

    print("\n  relocated addresses per section:")
    for s in secs:
        print("    %-10s %d" % (s["name"], counts.get(s["name"], 0)))
    if "<unmapped>" in counts:
        print("    <unmapped>      %d" % counts["<unmapped>"])

    localrm = sec_of.get(".localrm")
    print("\n  .localrm range  = 0x%X .. 0x%X" % localrm)
    in_localrm = [v for v in rl if localrm[0] <= v < localrm[1]]
    print("  relocations inside .localrm: %d" % len(in_localrm))
    if in_localrm:
        print("    %s" % ", ".join("0x%X" % v for v in sorted(in_localrm)[:40]))

    # The specific addresses the .localrm code hardcodes.
    probe = {
        "guard/flag slot (used by GetResourceManagerII)": 0x55200,
        "instance slot   (used by GetResourceManagerII)": 0x55204,
        "vptr A (+0x00 of object)": 0x55210,
        "vptr B (+0x04 of object)": 0x55214,
        "vptr C (+0x20 of object)": 0x55230,
        "vptr D (+0x44 of object)": 0x55254,
        "operator new IAT slot": 0x3328C,
        "operator delete IAT slot": 0x33284,
    }
    covered = set(rl)
    print("\n  are the hardcoded absolutes relocated?")
    verdict = {}
    for label, rva in probe.items():
        ok = rva in covered
        verdict[label] = {"rva": rva, "relocated": ok}
        print("    %-48s RVA 0x%-6X %s"
              % (label, rva, "RELOCATED" if ok else "*** NOT RELOCATED ***"))

    # vtable contents: are the 48 slot values themselves relocated?
    vtable_off = None
    for s in secs:
        if s["name"] == ".localrm":
            vtable_off = s["raw"] + 0x210
    vt = [struct.unpack_from("<I", d, vtable_off + i * 4)[0] for i in range(48)]
    vt_relo = sum(1 for i in range(48) if (0x55210 + i * 4) in covered)
    print("\n  vtable at .localrm+0x210 (%d slots):" % len(vt))
    print("    distinct values: %s" % ", ".join("0x%X" % v for v in sorted(set(vt))))
    print("    slots whose own address is relocated: %d/48" % vt_relo)

    n_notrel = sum(1 for v in verdict.values() if not v["relocated"])
    print("\nVERDICT: %d of %d hardcoded absolutes in .localrm are NOT relocated."
          % (n_notrel, len(verdict)))
    if n_notrel:
        delta = 0x12D40000 - preferred  # an actual observed load base
        print("  At an observed load base of 0x12D40000 the error would be")
        print("  (0x12D40000 - 0x%08X) = 0x%X per hardcoded address." % (preferred, delta))

    out = {
        "preferred_base": preferred,
        "reloc_dir_rva": rel_rva,
        "reloc_dir_size": rel_size,
        "reloc_blocks": nblocks,
        "reloc_entries": nent,
        "relocated_per_section": counts,
        "localrm_relocations": len(in_localrm),
        "hardcoded_absolutes": verdict,
        "hardcoded_absolutes_not_relocated": n_notrel,
        "vtable_distinct_values": sorted("0x%X" % v for v in set(vt)),
    }
    with open(os.path.join(OUT, "a08_localrm_relocs.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a08_localrm_relocs.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
