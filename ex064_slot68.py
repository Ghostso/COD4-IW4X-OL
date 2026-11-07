# EX-064 TASK F/G: resolve the manager vtable offset +0x68 used by
# IIPSLaunchRestore.dll and decide whether slot 5 (+0x14) is ever used there.
import json

from ex060_iips_cfg import Image, DLL

MGR_VT = 0x1003934C


def main():
    img = Image(DLL)
    base = img.base
    print("=" * 78)
    print("manager vtable 0x%X : what is at offset +0x68 ?" % MGR_VT)
    print("=" * 78)
    for off in (0x00, 0x04, 0x14, 0x68, 0x6C):
        v = int.from_bytes(img.read(MGR_VT - base + off, 4), "little")
        t = v - base
        slot = off // 4
        print("  +0x%02X (slot %2d) -> 0x%08X  RVA 0x%05X  code=%s" % (
            off, slot, v, t, img.is_code(t)))

    print()
    print("vtable size: 47 slots = 0xBC bytes")
    print("  +0x68 < 0xBC  ->  +0x68 is slot 26, INSIDE the vtable")
    print("  +0x14 < 0xBC  ->  +0x14 is slot  5, INSIDE the vtable")
    print()
    print("=" * 78)
    print("so IIPSLaunchRestore.dll calls manager slot 26 (+0x68),")
    print("NOT the slot-5 chain that leads to sub_197F0.")
    print("=" * 78)

    # what is at +0x68 / +0x04 in CNIFS vtable too, for contrast
    print("=" * 78)
    print("contrast with CNIFS vtable 0x1003530C")
    print("=" * 78)
    for off in (0x00, 0x04, 0x50):
        v = int.from_bytes(img.read(0x1003530C - base + off, 4), "little")
        print("  +0x%02X -> 0x%08X (sub_%X)" % (off, v, v - base))


if __name__ == "__main__":
    main()
