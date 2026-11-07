# Full disassembly of ResourceManagerII::OnRecvWndMsg @ 0x100154C0,
# the internal wnd-message dispatcher for pipe records (cmd 2..21).
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

    def annotate(ins):
        if "dword ptr [0x" in ins.op_str:
            try:
                target = int(ins.op_str.split("[")[1].split("]")[0], 16)
                name = iat.get(target)
                if name:
                    return "   ; " + name
            except ValueError:
                pass
        return ""

    start, end = 0x100154C0, 0x10015850
    off = pe.get_offset_from_rva(start - base)
    print("==== ResourceManagerII::OnRecvWndMsg 0x%08X..0x%08X ====" % (start, end))
    for ins in md.disasm(blob[off:off + (end - start)], start):
        print("  %08X  %-22s %s %s%s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, annotate(ins)))

    print()
    print("=== jump table @0x10015688 / byte table @0x100156AC ===")
    for va in (0x10015688, 0x100156AC):
        off = va - base
        print("0x%08X: %s" % (va, blob[off:off + 0x40].hex(" ")))


main()
