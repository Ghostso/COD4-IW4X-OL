import sys
import pefile

sys.stdout.reconfigure(encoding="utf-8")

IMAGE_BASE = 0x400000


def load(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    return pe


def rva_of(pe, va):
    return va - pe.OPTIONAL_HEADER.ImageBase


def read_va(pe, va, size):
    rva = rva_of(pe, va)
    return pe.get_data(rva, size)


def section_of(pe, va):
    rva = rva_of(pe, va)
    for section in pe.sections:
        name = section.Name.rstrip(b"\x00").decode("latin-1")
        start = section.VirtualAddress
        end = start + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if start <= rva < end:
            return name, start, section.PointerToRawData, section.SizeOfRawData
    return None, None, None, None


def main():
    path = "COD OL/codoMP_client_shipRetail.exe"
    pe = load(path)
    print("ImageBase = 0x%08X" % pe.OPTIONAL_HEADER.ImageBase)
    print("EntryPoint RVA = 0x%08X" % pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    print()
    print("Sections:")
    for section in pe.sections:
        name = section.Name.rstrip(b"\x00").decode("latin-1")
        print(
            "  %-10s VA=0x%08X VS=0x%08X RAW=0x%08X RSize=0x%08X flags=0x%08X"
            % (
                name,
                pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress,
                section.Misc_VirtualSize,
                section.PointerToRawData,
                section.SizeOfRawData,
                section.Characteristics,
            )
        )

    print()
    print("Requested VA probes (disk bytes):")
    for va in (0x4FD287, 0x4FCEE0, 0x808650, 0x77EE40, 0x7F26C0, 0x7F3600, 0xB991A0):
        data = read_va(pe, va, 16)
        sec, sva, praw, sraw = section_of(pe, va)
        print(
            "  0x%08X sec=%-8s raw=0x%08X : %s"
            % (va, sec, praw, " ".join("%02x" % b for b in data))
        )

    print()
    print("String probes (ASCII/UTF-16 in disk image):")
    needles = [
        b"dwauth.ini",
        b"stun.ini",
        b"buildconfig.ini",
        b"cacert.pem",
        b"https://%s/",
        b"/auth/",
        b"lsg_server_ticket",
        b"/title/",
        b"/queue/",
    ]
    for needle in needles:
        hits = []
        for section in pe.sections:
            raw = section.get_data()
            start = 0
            while True:
                idx = raw.find(needle, start)
                if idx < 0:
                    break
                va = (
                    pe.OPTIONAL_HEADER.ImageBase
                    + section.VirtualAddress
                    + idx
                )
                hits.append(va)
                start = idx + 1
        # UTF-16LE variant
        wide = needle.decode("latin-1").encode("utf-16-le")
        for section in pe.sections:
            raw = section.get_data()
            start = 0
            while True:
                idx = raw.find(wide, start)
                if idx < 0:
                    break
                va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + idx
                hits.append(va)
                start = idx + 1
        label = needle.decode("latin-1")
        print("  %-20s hits=%d %s" % (label, len(hits), ["0x%08X" % h for h in hits[:8]]))


if __name__ == "__main__":
    main()
