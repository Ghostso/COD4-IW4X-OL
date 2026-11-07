"""EB-003 Agent 11 - does the ORIGINAL iips.dll also depend on base 0x10000000?

Agent 10 found that Original iips.dll's exported code RVAs (0x1C80/0x1C60) are not
themselves in the relocation table -- which is expected, since those are instruction
bytes, not pointers. What matters is whether the *absolute operands* the code uses
are relocated. LOCALRM-006 decoded them as:

    GetResourceManagerII:  ... test byte [0x1004EB6C], 1 ; or dword [0x1004EB6C], 1
                               mov [0x1004EB68], eax
                               call 0x2BE34        (operator new, absolute)
    ReleaseResourceManagerII: mov eax,[ecx] ; mov edx,[eax] ; push 1 ; call edx

If those immediate operands ARE listed in .reloc, the original is base-independent
(the loader fixes them). If they are NOT, the original is also base-dependent and
the whole engine relies on the loader honouring 0x10000000 for it.

This distinction is the difference between "LocalRM_v3 has a bug" and "LocalRM_v3
has to live at the same base as the module it replaces".
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
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
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    rel_rva, rel_size = struct.unpack_from("<II", d, pe + 24 + 96 + 40)
    return d, pe, preferred, secs, rel_rva, rel_size


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def reloc_set(d, secs, rel_rva, rel_size):
    off = r2o(secs, rel_rva)
    out = {}
    if off is None:
        return out
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
            out[page + (w & 0xFFF)] = w >> 12      # keep the type nibble
        p += bsz
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    d, pe, preferred, secs, rel_rva, rel_size = parse(
        os.path.join(GAME, "IIPS", "iips.dll"))
    rel = reloc_set(d, secs, rel_rva, rel_size)

    print("=== EB-003 Agent 11: is the ORIGINAL iips.dll base-independent? ===")
    print("  preferred base = 0x%08X" % preferred)
    print("  relocations    = %d" % len(rel))
    print()

    # The absolute operands LOCALRM-006 decoded out of the two exports.
    probes = {
        "singleton guard dword  [0x1004EB6C]": 0x4EB6C,
        "singleton slot  dword  [0x1004EB68]": 0x4EB68,
        "SEH scope table 0x100325A9 (push imm32)": 0x325A9,
        "/GS cookie      0x10042020": 0x42020,
        "operator new    0x2BE34  (call rel32 target is RVA; not relocated)": 0x2BE34,
    }
    print("  relocation coverage of the decoded absolute operands:")
    res = {}
    for label, rva in probes.items():
        t = rel.get(rva)
        res[label] = {"rva": rva, "relocated": t is not None,
                      "type": ("IMAGE_REL_BASED_%s" % {3: "HIGHLOW", 0: "ABSOLUTE"}.get(t, t))
                      if t is not None else None}
        print("    %-62s %s" % (label, ("YES type=%s" % t) if t is not None else "no"))

    # Where do the export bodies live, and is that section relocated at all?
    print()
    for name, rva in (("GetResourceManagerII", 0x1C80),
                      ("ReleaseResourceManagerII", 0x1C60)):
        sec = next((s for s in secs
                    if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"])), None)
        print("  %-26s RVA 0x%-6X is in section %s" % (name, rva, sec["name"] if sec else "?"))

    guard_rel = res["singleton guard dword  [0x1004EB6C]"]["relocated"]
    slot_rel = res["singleton slot  dword  [0x1004EB68]"]["relocated"]
    print()
    if guard_rel and slot_rel:
        verdict = ("The original's singleton guard and slot operands ARE relocated, "
                   "so the original is base-INDEPENDENT: the loader patches them "
                   "wherever the module lands.")
    elif guard_rel or slot_rel:
        verdict = ("Only one of the original's two singleton operands is relocated; "
                   "the original is partially base-dependent.")
    else:
        verdict = ("The original's singleton operands are NOT relocated either, so "
                   "the original is ALSO base-dependent and the engine relies on the "
                   "loader placing iips.dll at 0x10000000.")
    print("VERDICT: %s" % verdict)

    out = {
        "file": "IIPS\\iips.dll",
        "preferred_base": preferred,
        "relocation_count": len(rel),
        "operand_coverage": res,
        "verdict": verdict,
    }
    with open(os.path.join(OUT, "a11_original_base_dep.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "a11_original_base_dep.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
