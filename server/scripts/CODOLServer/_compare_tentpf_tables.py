import struct

import pefile

IIPS = r"COD OL\IIPS\Tenio\TenTPF.dll"
CROSS = r"COD OL\Cross\Tenio\TenTPF.dll"


def read_table(path, count_va, table_va, limit=1024):
    pe = pefile.PE(path, fast_load=True)
    data = open(path, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase

    def dword(va):
        try:
            off = pe.get_offset_from_rva(va - base)
        except Exception:
            return None
        if off is None or off < 0 or off + 4 > len(data):
            return None
        return struct.unpack_from("<I", data, off)[0]

    count = dword(count_va)
    ids = []
    if count and 0 < count <= limit:
        for i in range(count):
            v = dword(table_va + i * 8)
            if v is None:
                break
            ids.append(v)
    return base, count, ids


def main():
    print("=" * 90)
    base, count, iips_ids = read_table(IIPS, 0x10438B80, 0x10438B84)
    print("IIPS 2012 TenTPF")
    print(f"  imagebase=0x{base:X} count_slot=0x{count} ids={len(iips_ids)}")
    print(f"  has985={985 in iips_ids}")
    print(f"  ids={iips_ids[:40]}{' ...' if len(iips_ids) > 40 else ''}")

    print("=" * 90)
    # Cross build is a different layout; find its table by scanning the data
    # section for a count/index pair that points at a plausible ID array.
    pe = pefile.PE(CROSS, fast_load=True)
    data = open(CROSS, "rb").read()
    cbase = pe.OPTIONAL_HEADER.ImageBase
    print("Cross 2013 TenTPF")
    print(f"  imagebase=0x{cbase:X}")

    # The 2013 build referenced 0x10222d2c..0x10222d30 region in the export stub.
    for count_va, table_va in (
        (0x10222D2C, 0x10223220),
        (0x10222D28, 0x10223220),
        (0x10222D2C, 0x10222D30),
    ):
        try:
            coff = pe.get_offset_from_rva(count_va - cbase)
            toff = pe.get_offset_from_rva(table_va - cbase)
        except Exception:
            continue
        if coff is None or toff is None:
            continue
        c = struct.unpack_from("<I", data, coff)[0] if coff + 4 <= len(data) else None
        print(f"  probe count_va=0x{count_va:X} -> {c}  table_va=0x{table_va:X}")
        if c and 0 < c <= 1024:
            ids = []
            for i in range(c):
                p = toff + i * 8
                if p + 4 > len(data):
                    break
                ids.append(struct.unpack_from("<I", data, p)[0])
            print(f"    ids={len(ids)} has985={985 in ids}")
            print(f"    sample={ids[:40]}")


if __name__ == "__main__":
    main()
