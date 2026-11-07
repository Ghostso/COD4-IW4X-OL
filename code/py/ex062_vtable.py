# EX-062 TASK C/E: reconstruct every vtable the CNIFS constructor installs,
# resolve every slot to a target RVA, and check whether InitInGameApp or
# sub_197F0 appear in any of them.
#
# Read-only. No patching, no dynamic execution.
import json
from collections import OrderedDict

from ex060_iips_cfg import Image, DLL, build_imports


def main():
    img = Image(DLL)
    base = img.base
    imp = build_imports(img)

    # The vtable immediates installed by sub_90D0, from EX-061.
    vt_imms = [
        (0x90F8, "ebp", 0x00, 0x10035204),
        (0x9105, "ebp", 0x04, 0x100352EC),
        (0x911A, "ebp", 0x50, 0x100351F8),
        (0x9126, "esi", None, 0x10035408),   # esi = ebp+8
        (0x9134, "ebp", 0x00, 0x1003530C),
        (0x913B, "ebp", 0x04, 0x100353E8),
        (0x9142, "ebp", 0x50, 0x10035418),
    ]

    print("=" * 78)
    print("CNIFS constructor vtable immediates")
    print("=" * 78)
    seen = OrderedDict()
    for rva, breg, disp, val in vt_imms:
        print("  0x%05X  [%s+%s] = 0x%X   (VA -> RVA 0x%X)" % (
            rva, breg, ("0x%X" % disp) if disp is not None else "(esi)",
            val, val - base))
        seen.setdefault(val, []).append((rva, breg, disp))

    print()
    print("distinct vtable addresses: %d" % len(seen))
    for va in sorted(seen):
        print("   0x%X   installed by %s" % (
            va, ", ".join("0x%X" % r for r, _, _ in seen[va])))

    # Dump each vtable: walk 4-byte pointers until we leave .rdata
    print()
    print("=" * 78)
    print("vtable contents")
    print("=" * 78)
    result = {}
    for va in sorted(seen):
        rva = va - base
        print()
        print("-- vtable 0x%X (RVA 0x%X)" % (va, rva))
        entries = []
        i = 0
        while i < 0x80:
            slot_rva = rva + i * 4
            if not img.is_mapped(slot_rva):
                break
            raw = img.read(slot_rva, 4)
            if len(raw) < 4:
                break
            val = int.from_bytes(raw, "little")
            if not (img.base <= val < img.base + img.size):
                break
            tgt = val - base
            if not img.is_code(tgt):
                break
            entries.append((i, slot_rva, val, tgt))
            print("     slot %-2d  +0x%02X  RVA 0x%05X  -> 0x%08X (sub_%X)"
                  % (i, i * 4, slot_rva, val, tgt))
            i += 1
        result[va] = entries
        if not entries:
            print("     (no code pointers -- not a vtable, or fully indirect)")

    # KEY CHECK: does any slot resolve to InitInGameApp (0x9860) or
    # sub_197F0 (0x197F0)?
    print()
    print("=" * 78)
    print("KEY CHECK: do any vtable slots point at InitInGameApp / sub_197F0?")
    print("=" * 78)
    interest = {0x9860: "CNIFS::InitInGameApp", 0x197F0: "sub_197F0",
                0x9570: "CNIFS::initIfsLib", 0x90D0: "CNIFS::ctor",
                0x9240: "CNIFS::dtor"}
    found = False
    for va, entries in result.items():
        for idx, slot_rva, val, tgt in entries:
            if tgt in interest:
                print("   vtable 0x%X slot %d -> %s (0x%X)" % (
                    va, idx, interest[tgt], tgt))
                found = True
    if not found:
        print("   NONE")

    out = {
        "vtables": {
            "0x%X" % va: [{"slot": i, "slot_rva": "0x%X" % s,
                           "value": "0x%X" % v, "target": "0x%X" % t}
                          for i, s, v, t in entries]
            for va, entries in result.items()
        }
    }
    with open("ex062_vtables.json", "w") as f:
        json.dump(out, f, indent=1)
    print()
    print("wrote ex062_vtables.json")


if __name__ == "__main__":
    main()
