# Disassemble the OnRecvMsg wrapper and SetHostAction reply builder to pin
# cmd @ +2, userdata @ +6, and the reply-message header fields.
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PIPE = r"COD OL\IIPS\iips.dll"


def main():
    pe = pefile.PE(PIPE)
    base = pe.OPTIONAL_HEADER.ImageBase
    blob = open(PIPE, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    iat = {}
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in entry.imports:
            if imp.name:
                iat[imp.address] = imp.name.decode()

    def dis(start, end, label):
        off = pe.get_offset_from_rva(start - base)
        print("==== %s 0x%08X..0x%08X ====" % (label, start, end))
        for ins in md.disasm(blob[off:off + (end - start)], start):
            extra = ""
            if "dword ptr [0x" in ins.op_str:
                try:
                    target = int(ins.op_str.split("[")[1].split("]")[0], 16)
                    name = iat.get(target)
                    if name:
                        extra = "   ; " + name
                except ValueError:
                    pass
            print("  %08X  %-22s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
        print()

    dis(0x10015280, 0x100153B0, "ResourceManagerII::OnRecvMsg wrapper")
    dis(0x100151E0, 0x10015280, "before OnRecvMsg wrapper")

    # Resolve the format string used by SetHostAction at the beginning.
    for va in (0x100375C8, 0x1003709C, 0x100370D0):
        off = va - base
        print("string 0x%08X: %r" % (va, blob[off:off + 256].split(b"\0")[0]))


main()
