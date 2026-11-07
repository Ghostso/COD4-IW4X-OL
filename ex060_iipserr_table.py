# EX-060 TASK 4: determine how IIPSERR_* strings are referenced.
import re
import struct
from collections import OrderedDict

from ex060_iips_cfg import Image, DLL


def rva_for_raw(img, off):
    for s in img.sections:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return s["va"] + (off - s["raw"])
    return None


def main():
    img = Image(DLL)
    raw = open(DLL, "rb").read()

    names = sorted(set(m.group().decode()
                       for m in re.finditer(rb"IIPSERR_[A-Z_]+", raw)))
    print("distinct IIPSERR_* strings:", len(names))
    va_of = {}
    for n in names:
        i = raw.find(n.encode())
        rva = rva_for_raw(img, i)
        va_of[n] = img.base + rva

    # pointer refs (4-byte LE) anywhere in file
    print()
    print("=== pointer refs (le32) to each IIPSERR_* string ===")
    for n in names:
        va = va_of[n]
        needle = struct.pack("<I", va)
        refs = []
        st = 0
        while True:
            i = raw.find(needle, st)
            if i < 0:
                break
            refs.append(i)
            st = i + 1
        if refs:
            print("  %-46s VA 0x%08X refs=%d" % (n, va, len(refs)))
            for r in refs[:8]:
                rva = rva_for_raw(img, r)
                print("      raw 0x%06X RVA 0x%06X VA 0x%08X" % (
                    r, rva, img.base + rva))

    print()
    print("=== contiguous region containing the IIPSERR_* block ===")
    first = min(raw.find(n.encode()) for n in names)
    last = max(raw.find(n.encode()) + len(n) for n in names)
    print("  raw 0x%X .. 0x%X  (size 0x%X)" % (first, last, last - first))
    print("  VA  0x%08X .. 0x%08X" % (
        img.base + rva_for_raw(img, first),
        img.base + rva_for_raw(img, last)))

    # Does the file contain a table of these VAs in .rdata?
    print()
    print("=== scan .rdata (0x33000..0x42000) for a pointer table ===")
    count = 0
    for rva in range(0x33000, 0x42000, 4):
        val = struct.unpack_from("<I", img.by_rva, rva)[0]
        for n, va in va_of.items():
            if val == va:
                print("  .rdata+0x%X -> %s" % (rva, n))
                count += 1
    if count == 0:
        print("  no pointer table found in .rdata")


if __name__ == "__main__":
    main()
