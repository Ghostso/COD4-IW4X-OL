# EX-063 TASK D/G: resolve the crux.
#
# Question: at sub_1A26E+0x1A2FC the code reads [esi+0x19C] and then
# dispatches [vt+0x04].  EX-062 established that sub_12760 writes the
# CNIFS* into [ESI+0x19C] at 0x12D06.
#
# If the CNIFS primary vtable is 0x1003530C, then [cnifs+0x04] is the
# CNIFS SECONDARY vtable pointer (a DATA pointer), not a code pointer.
# So a `mov edx,[eax+4]; call edx` on CNIFS would be wrong.
#
# => therefore [esi+0x19C] in sub_1A26E must be a DIFFERENT object than
#    the one sub_12760 published, OR the vtable at [ecx] is not 0x1003530C.
#
# Resolve by checking the two candidate vtables and what slot+4 holds.
import json

from ex060_iips_cfg import Image, DLL

CNIFS_VT = 0x1003530C
MGR_VT = 0x1003934C


def main():
    img = Image(DLL)
    base = img.base

    print("=" * 78)
    print("the two candidate vtables and their slot +0x04")
    print("=" * 78)
    for name, va in (("CNIFS primary", CNIFS_VT),
                     ("manager primary", MGR_VT)):
        v0 = int.from_bytes(img.read(va - base, 4), "little")
        v1 = int.from_bytes(img.read(va - base + 4, 4), "little")
        print("  %-16s vt=0x%X" % (name, va))
        print("      slot 0 = 0x%08X  (RVA 0x%X)  code=%s" % (
            v0, v0 - base, img.is_code(v0 - base)))
        print("      slot 1 = 0x%08X  (RVA 0x%X)  code=%s" % (
            v1, v1 - base, img.is_code(v1 - base)))

    print()
    print("=" * 78)
    print("so: which vtable makes `mov edx,[eax+4]; call edx` legal?")
    print("=" * 78)
    print("""
  CNIFS primary 0x1003530C:
     [vt+0] = 0x100076D0   code
     [vt+4] = 0x10007700   code      <- slot 1 IS a code pointer

  BOTH vtables have code pointers in slot 1.

  Therefore `mov eax,[ecx]; mov edx,[eax+4]; call edx` is legal for
  EITHER object, and the identity of the object at [esi+0x19C] in
  sub_1A26E must be decided by the OBJECT, not by the slot shape.
""")

    print("=" * 78)
    print("is slot 1 of the CNIFS vtable sub_197F0 (0x197F0)?")
    print("=" * 78)
    c1 = int.from_bytes(img.read(CNIFS_VT - base + 4, 4), "little") - base
    m1 = int.from_bytes(img.read(MGR_VT - base + 4, 4), "little") - base
    print("   CNIFS  vt slot 1 -> sub_%X" % c1)
    print("   manager vt slot 1 -> sub_%X" % m1)
    print()
    print("   sub_197F0 is 0x197F0")
    print("   CNIFS  matches : %s" % (c1 == 0x197F0))
    print("   manager matches: %s" % (m1 == 0x197F0))

    print()
    print("=" * 78)
    print("consequence")
    print("=" * 78)
    if m1 == 0x197F0 and c1 != 0x197F0:
        print("""
  sub_197F0 is slot 1 of the MANAGER vtable 0x1003934C, NOT of CNIFS.

  Therefore in sub_1A26E:
      0x1A2FC  mov ecx, [esi+0x19C]
      0x1A302  mov eax, [ecx]
      0x1A304  mov edx, [eax+4]
      0x1A309  call edx

  the object at [esi+0x19C] must be a MANAGER object whose vtable is
  0x1003934C -- NOT the CNIFS object that sub_12760 publishes at
  [parent+0x19C].

  => [X+0x19C] is a SHARED OFFSET NAME used by at least TWO different
     classes.  EX-062's finding is specific to the parent object used by
     sub_12760.  It must NOT be generalised to every [..+0x19C] reader.
""")
    else:
        print("   unexpected; inspect manually")


if __name__ == "__main__":
    main()
