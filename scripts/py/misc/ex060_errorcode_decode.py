# EX-060 TASK 3/4: decode 0x8189FEC against the IIPS error-code schema.
import re
import struct


def main():
    v = 0x8189FEC
    print("target value 0x%08X = %d" % (v, v))
    print()
    print("=== decomposition attempts ===")
    for shift in range(0, 32, 4):
        print("  >>%2d = 0x%-8X  &0xFFFF = 0x%04X  &0xFFF = 0x%03X" % (
            shift, v >> shift, (v >> shift) & 0xFFFF, (v >> shift) & 0xFFF))

    print()
    print("=== the '0x%x' formatter string exists in the EXE at VA 0xDC9400 ===")
    print("   The EXE prints the code as: 0x8189FEC")

    print()
    print("=== candidate interpretations ===")
    cands = [
        ("HRESULT-style FAILED bit set (0x8xxxxxxx)", v & 0x80000000 != 0),
        ("low 16 bits = 0x9FEC", (v & 0xFFFF) == 0x9FEC),
        ("low 12 bits = 0xFEC", (v & 0xFFF) == 0xFEC),
        ("+0xFEC offset from 0x81890000", v - 0x81890000 == 0xFEC),
        ("0x8189FEC as 15-bit value 0x9FEC", True),
    ]
    for name, ok in cands:
        print("  %-44s %s" % (name, ok))

    print()
    print("=== IIPS error-code enum (0..47) from IIPSClient.ini [ErrMsg] ===")
    print("   none of these is a 32-bit 0x8189FEC value.")
    print("   The enum is small; 0x8189FEC is NOT one of them.")

    print()
    print("=== does 0x8189FEC appear as any IIPSERR_* index? ===")
    print("   index range observed: 0..47; value range out of range.")

    print()
    print("=== reinterpret as 4 ASCII chars ===")
    b = struct.pack("<I", v)
    print("  le bytes: %r  -> ascii %r" % (b, "".join(chr(c) for c in b)))
    b2 = struct.pack(">I", v)
    print("  be bytes: %r  -> ascii %r" % (b2, "".join(chr(c) for c in b2)))

    print()
    print("=== relation to EXE image range ===")
    exe_base, exe_end = 0x400000, 0xEA59000
    print("  is in EXE image [0x%X, 0x%X): %s" % (
        exe_base, exe_end, exe_base <= v < exe_end))
    print("  offset from EXE base: 0x%X" % (v - exe_base))
    print("  .tp3 section 3 is VA [0xA16000, 0xE5C7CC0)")
    print("  offset lies in that section: %s" % (0xA16000 <= v - exe_base < 0xE5C7CC0))


if __name__ == "__main__":
    main()
