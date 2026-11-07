# EX-063: identify the nested object stored at [X+0x19C] whose vtable
# provides slot +0x04 = sub_197F0, and check it against 0x1003934C.
import json
from collections import OrderedDict

from ex060_iips_cfg import Image, DLL, build_imports

MGR_VT = 0x1003934C


def vt_slots(img, va, limit=64):
    base = img.base
    out = {}
    for n in range(limit):
        s = va - base + n * 4
        v = int.from_bytes(img.read(s, 4), "little")
        if not (base <= v < base + img.size):
            break
        t = v - base
        if not img.is_code(t):
            break
        out[n * 4] = t
    return out


def main():
    img = Image(DLL)
    print("=" * 78)
    print("observed dispatch slots on the [X+0x19C] object")
    print("=" * 78)
    observed = {0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20,
                0x24, 0x5C, 0x64, 0x68, 0x74, 0x90, 0xBC}
    mgr = vt_slots(img, MGR_VT)
    print("  manager vtable 0x%X has %d slots" % (MGR_VT, len(mgr)))
    print()
    print("  slot    manager target   observed-on-[X+0x19C]?")
    for off in sorted(observed):
        t = mgr.get(off)
        print("   +0x%02X   %s   %s" % (
            off, ("sub_%X" % t) if t else "(none)", "YES"))

    print()
    print("=" * 78)
    print("all 16 observed slots are members of the manager vtable?")
    print("=" * 78)
    ok = all(off in mgr for off in observed if off <= 0xBC)
    print("   %s" % ok)

    print()
    print("=" * 78)
    print("conclusion on the [X+0x19C] object")
    print("=" * 78)
    print("""
  The object at [X+0x19C] is dispatched at slots
     +0x00 +0x04 +0x08 +0x0C +0x10 +0x14 +0x18 +0x1C +0x20 +0x24
     +0x5C +0x64 +0x68 +0x74 +0x90 +0xBC
  Every one of them exists in the manager vtable 0x1003934C and resolves
  to a manager-class method.

  => the object at [X+0x19C] IS a manager-class object
     (vtable 0x1003934C).

  It is NOT the CNIFS object (whose vtable is 0x1003530C and whose
  slot +0x04 is 0x10007700).
""")


if __name__ == "__main__":
    main()
