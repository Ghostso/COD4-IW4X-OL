# Full disassembly of ResourceManagerII::SetHostAction @ 0x10016DD0
# (called from OnRecvMsg cmd==1 with userdata = *(u32*)(edi+6)).
# Goal: pin down the 791-byte record field layout for cmd=1 / cmd=2.
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PIPE = r"COD OL\IIPS\iips.dll"


def main():
    pe = pefile.PE(PIPE)
    base = pe.OPTIONAL_HEADER.ImageBase
    blob = open(PIPE, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    iat = {}
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in entry.imports:
            if imp.name:
                iat[imp.address] = imp.name.decode()

    def annotate(ins):
        txt = ins.op_str
        if "dword ptr [0x" in txt:
            try:
                target = int(txt.split("[")[1].split("]")[0], 16)
                name = iat.get(target)
                if name:
                    return "   ; " + name
            except ValueError:
                pass
        return ""

    def dis(start, end, label):
        offset = pe.get_offset_from_rva(start - base)
        print("==== %s  0x%08X .. 0x%08X ====" % (label, start, end))
        count = 0
        for ins in md.disasm(blob[offset:offset + (end - start)], start):
            print("  %08X  %-22s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str,
                annotate(ins)))
            count += 1
            if count > 260:
                print("  ... truncated")
                break
        print()

    dis(0x10016DD0, 0x10017050, "ResourceManagerII::SetHostAction")


main()
