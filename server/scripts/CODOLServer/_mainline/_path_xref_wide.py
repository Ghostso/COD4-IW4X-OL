# Resolve wide-string VAs and find x86 references in the two TPFUI binaries.
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

CASES = [
    (r"COD OL\IIPS\IIPSHostApp.exe", [
        "TPFUI", "IIPSRes", "back",
        "IIPS", "LoadImage", "CreateComponent",
    ]),
    (r"COD OL\IIPS\Tenio\June.dll", [
        "LoadImageFromBuffer", "GetBuffer", "LoadImage", "TPFFile",
    ]),
    (r"COD OL\IIPS\Tenio\TenTPF.dll", [
        "CTPFImageCreator", "LoadImage", "TPFFile",
    ]),
]


def wide(text):
    return "".join(ch + "\x00" for ch in text).encode("latin1")


def main():
    for path, needles in CASES:
        pe = pefile.PE(path)
        base = pe.OPTIONAL_HEADER.ImageBase
        blob = open(path, "rb").read()
        print("===== %s base=0x%08X =====" % (path, base))

        wanted = {}
        for needle in needles:
            for kind, seq in (("A", needle.encode("latin1")),
                              ("W", wide(needle))):
                start = 0
                while True:
                    pos = blob.find(seq, start)
                    if pos < 0:
                        break
                    try:
                        va = base + pe.get_rva_from_offset(pos)
                    except pefile.PEFormatError:
                        va = None
                    if va is not None:
                        wanted[va] = (kind, needle, pos)
                    start = pos + 1

        for va in sorted(wanted):
            kind, needle, off = wanted[va]
            print("  str [%s] %-24s off=0x%06X VA=0x%08X" % (
                kind, needle, off, va))

        targets = set(wanted)
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        print("  xrefs:")
        for sec in pe.sections:
            if not (sec.Characteristics & 0x20000000):
                continue
            raw = blob[sec.PointerToRawData:
                       sec.PointerToRawData + sec.SizeOfRawData]
            sec_va = base + sec.VirtualAddress
            for ins in md.disasm(raw, sec_va):
                if ins.mnemonic not in ("push", "mov", "lea"):
                    continue
                for target in targets:
                    token = "0x%x" % target
                    if token in ins.op_str:
                        kind, needle, off = wanted[target]
                        print("    0x%08X  %-24s %s %s   ; %s" % (
                            ins.address, ins.bytes.hex(),
                            ins.mnemonic, ins.op_str, needle))
        print()


main()
