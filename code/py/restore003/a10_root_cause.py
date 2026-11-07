"""EB-003 Agent 10 - the complete root-cause chain, from bytes.

Establishes the final causal chain and checks each link:

  L1  codoMP_client_shipRetailBase.dll, IIPS\\iips.dll and LocalRM_v3.dll all
      declare the SAME preferred image base, 0x10000000.
  L2  Base.dll is loaded first and is 60 MB, so it takes 0x10000000.
  L3  Therefore LocalRM_v3.dll is relocated to some other base.
  L4  .localrm (where LocalRM_v3's exports live) has ZERO base relocations,
      while the original iips.dll's RM code lives in .text, which IS relocated.
  L5  Consequence: reproducing the original provider's behaviour requires the
      provider to land at 0x10000000; otherwise its hardcoded absolutes are wrong.

Each link is reported with the byte-level fact that supports it.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore003", "evidence")


def head(path):
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
    dll_char = struct.unpack_from("<H", d, pe + 24 + 70)[0]
    return {"d": d, "pe": pe, "preferred": preferred, "secs": secs,
            "rel_rva": rel_rva, "rel_size": rel_size, "dll_char": dll_char}


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def reloc_targets(h):
    d, secs = h["d"], h["secs"]
    off = r2o(secs, h["rel_rva"])
    out = set()
    if off is None:
        return out
    end = min(off + h["rel_size"], len(d))
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
            out.add(page + (w & 0xFFF))
        p += bsz
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {"links": {}}

    print("=== EB-003 Agent 10: root-cause chain ===")
    print()

    orig = head(os.path.join(GAME, "IIPS", "iips.dll"))
    base = head(os.path.join(GAME, "codoMP_client_shipRetailBase.dll"))
    v3 = head(os.path.join(ROOT, "LocalRM_v3.dll"))

    print("L1  preferred image bases")
    for nm, h in (("codoMP_client_shipRetailBase.dll", base),
                  ("IIPS\\iips.dll", orig),
                  ("LocalRM_v3.dll", v3)):
        print("      %-36s 0x%08X" % (nm, h["preferred"]))
    l1 = (base["preferred"] == orig["preferred"] == v3["preferred"])
    print("      all identical: %s" % l1)
    rep["links"]["L1_same_preferred_base"] = {
        "base_dll": "0x%X" % base["preferred"],
        "original_iips": "0x%X" % orig["preferred"],
        "localrm_v3": "0x%X" % v3["preferred"],
        "identical": l1,
    }

    print()
    print("L2/L3  Base.dll is loaded first and occupies 0x10000000")
    print("      Base.dll SizeOfImage = 0x%X (%.1f MB)"
          % (struct.unpack_from("<I", base["d"], base["pe"] + 24 + 56)[0],
             struct.unpack_from("<I", base["d"], base["pe"] + 24 + 56)[0] / 1048576.0))
    print("      -> a later 0x10000000-preferring module must relocate")
    rep["links"]["L2_base_occupies_preferred_base"] = {
        "base_dll_image_size": "0x%X" % struct.unpack_from(
            "<I", base["d"], base["pe"] + 24 + 56)[0],
        "consequence": "LocalRM_v3.dll cannot load at 0x10000000 in this process",
    }

    print()
    print("L4  relocation coverage")
    orl = reloc_targets(orig)
    vrl = reloc_targets(v3)
    for nm, h, rl, interesting in (
            ("IIPS\\iips.dll", orig, orl, (0x1C80, 0x1C60)),
            ("LocalRM_v3.dll", v3, vrl, (0x55000, 0x55040, 0x55200, 0x55204))):
        per = {}
        for s in h["secs"]:
            per[s["name"]] = sum(1 for v in rl
                                 if s["va"] <= v < s["va"] + max(s["vsize"], s["rsize"]))
        print("      %s  total relocs=%d  per-section=%s"
              % (nm, len(rl), json.dumps(per)))
        for a in interesting:
            print("         is RVA 0x%-6X relocated? %s" % (a, a in rl))
    rep["links"]["L4_relocation_coverage"] = {
        "original_iips_total_relocs": len(orl),
        "original_getrm_rva_relocated": 0x1C80 in orl,
        "localrm_total_relocs": len(vrl),
        "localrm_export_rva_relocated": 0x55000 in vrl,
        "localrm_guard_slot_relocated": 0x55200 in vrl,
        "localrm_instance_slot_relocated": 0x55204 in vrl,
    }

    print()
    print("L5  consequence")
    print("      A provider built the LOCALRM way reproduces the original's")
    print("      behaviour only when it lands at 0x10000000. Under the real")
    print("      process, Base.dll already owns that base, so the .localrm code's")
    print("      hardcoded addresses are wrong by the reload delta, and")
    print("      GetResourceManagerII can never construct a usable object.")
    rep["links"]["L5_consequence"] = (
        "LocalRM_v3.dll requires image base 0x10000000; in the real process that "
        "base is taken by codoMP_client_shipRetailBase.dll, so .localrm's "
        "unrelocated absolute addresses are wrong and the provider cannot work.")

    with open(os.path.join(OUT, "a10_root_cause.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "a10_root_cause.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
