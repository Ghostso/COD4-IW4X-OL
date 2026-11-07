# Disassemble IIPSHostApp.exe around the wide-string xref to "TPFUI"
# and dump the adjacent wide-string table, to identify the exact path
# construction instruction sequence.
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PATH = r"COD OL\IIPS\IIPSHostApp.exe"


def main():
    pe = pefile.PE(PATH)
    base = pe.OPTIONAL_HEADER.ImageBase
    blob = open(PATH, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    # Dump UTF-16LE strings in the 0x420700..0x420D00 VA range.
    lo = 0x420700 - base
    hi = 0x420D00 - base
    print("=== wide strings 0x420700..0x420D00 ===")
    pos = lo
    while pos < hi:
        end = blob.find(b"\x00\x00", pos)
        if end < 0 or end > hi:
            break
        # Align: a UTF-16 string starts on an odd byte offset in this table.
        if (end - pos) >= 2 and (end - pos) % 2 == 0:
            raw = blob[pos:end + 2]
            try:
                text = raw.decode("utf-16-le")
            except UnicodeDecodeError:
                text = repr(raw)
            print("  VA 0x%08X  %r" % (base + pos, text))
        pos = end + 2
        while pos < hi and blob[pos:pos + 1] == b"\x00":
            pos += 1

    def dis(start, end, label):
        off = pe.get_offset_from_rva(start - base)
        print()
        print("==== %s 0x%08X..0x%08X ====" % (label, start, end))
        for ins in md.disasm(blob[off:off + (end - start)], start):
            print("  %08X  %-24s %s %s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    dis(0x40A850, 0x40A9A0, "exact TPFUI path build")


main()
