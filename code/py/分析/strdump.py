import sys
import pefile

sys.stdout.reconfigure(encoding="utf-8")

PATH = "COD OL/codoMP_client_shipRetail.exe"


def strings_near(pe, va, radius, min_len=4):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    raw = pe.get_data(max(0, rva - radius), radius * 2)
    base = rva - radius
    out = []
    current = bytearray()
    start = 0
    for i, byte in enumerate(raw):
        if 0x20 <= byte < 0x7F:
            if not current:
                start = i
            current.append(byte)
        else:
            if len(current) >= min_len:
                out.append((base + start, current.decode("latin-1")))
            current = bytearray()
    if len(current) >= min_len:
        out.append((base + start, current.decode("latin-1")))
    return out


def main():
    pe = pefile.PE(PATH, fast_load=True)
    pe.parse_data_directories()
    for va in (
        0x00D5A0E8,
        0x00D5A129,
        0x00D5A2D9,
        0x00DDBD9C,
        0x00DE09E4,
        0x00DC9CA4,
    ):
        print("===== around 0x%08X =====" % va)
        for rva, text in strings_near(pe, va, 0x200):
            print(
                "  0x%08X (rva 0x%08X)  %s"
                % (pe.OPTIONAL_HEADER.ImageBase + rva, rva, text)
            )
        print()


if __name__ == "__main__":
    main()
