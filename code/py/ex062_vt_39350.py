# EX-062 TASK I/F: identify the vtable that owns sub_197F0 (RVA 0x39350)
# and the full relationship map between the factory, the CNIFS vtables,
# and InitInGameApp.
import json

from ex060_iips_cfg import Image, DLL, build_imports


def vt_start(img, rva):
    """Walk backwards to the first slot of the vtable containing rva."""
    s = rva
    while s - 4 >= 0x33000:
        raw = img.read(s - 4, 4)
        if len(raw) < 4:
            break
        v = int.from_bytes(raw, "little")
        if not (img.base <= v < img.base + img.size):
            break
        t = v - img.base
        if not img.is_code(t):
            break
        s -= 4
    return s


def vt_dump(img, start, limit=64):
    out = []
    for i in range(limit):
        s = start + i * 4
        raw = img.read(s, 4)
        if len(raw) < 4:
            break
        v = int.from_bytes(raw, "little")
        if not (img.base <= v < img.base + img.size):
            break
        t = v - img.base
        if not img.is_code(t):
            break
        out.append((i, s, v, t))
    return out


def main():
    img = Image(DLL)

    print("=" * 78)
    print("vtable containing sub_197F0 (RVA 0x39350)")
    print("=" * 78)
    start = vt_start(img, 0x39350)
    print("   vtable start RVA 0x%X  VA 0x%X" % (start, img.base + start))
    slots = vt_dump(img, start)
    for i, s, v, t in slots:
        mark = "   <<< sub_197F0" if t == 0x197F0 else ""
        print("      slot %-2d +0x%02X  RVA 0x%05X -> 0x%08X (sub_%X)%s" % (
            i, i * 4, s, v, t, mark))

    print()
    print("=" * 78)
    print("summary: the three CNIFS-relevant entrypoints")
    print("=" * 78)
    print("""
   sub_197F0   RVA 0x197F0   member of vtable @ RVA 0x%X
   sub_12760   RVA 0x12760   factory: alloc + ctor + publish + DISPATCH
   sub_9860    RVA 0x9860    CNIFS primary vtable 0x1003530C slot 20
""" % start)

    print("=" * 78)
    print("relationship (instruction level)")
    print("=" * 78)
    print("""
   sub_197F0  (0x197F0)                 <- vtable @ 0x%X slot ?
     0x197F7  call sub_12760            ; the FACTORY
     0x197FC  test al,al
     0x197FE  jne 0x1980D               ; success -> AL = 1
     0x19800  mov ecx, esi              ; esi = this (from 0x197F5)
     0x19802  call sub_19820            ; cleanup/uninit path
     0x19807  xor al,al                 ; failure -> AL = 0
     0x1980E  ret 4

   sub_197F0  does NOT call 0x9860 directly.
   sub_197F0  reaches InitInGameApp only THROUGH sub_12760's
              vtable dispatch at 0x12F56.

   => sub_197F0  =  "initialise this object" vtable entry
      sub_12760  =  the actual lifecycle driver
      sub_9860   =  CNIFS vtable slot +0x50, invoked by sub_12760
""" % start)


if __name__ == "__main__":
    main()
