# EX-060: disassemble the EXE sites that reference the IIPS error strings.
import os
import struct

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")


def load(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    return pe, open(path, "rb").read()


def rva_to_raw(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(
                s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


def main():
    pe, data = load(EXE)
    base = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    sites = [
        ("WIN_IIPS_PREDOWNLOAD_ERROR", 0x58F104),
        ("WIN_IIPS_DLL_ERROR", 0x58F35E),
        ("WIN_IIPS_INIT_FAILED", 0x58F3CD),
    ]
    for name, va in sites:
        print("=" * 78)
        print("REF SITE %s @ VA 0x%X" % (name, va))
        print("=" * 78)
        start_rva = va - base - 0x80
        off = rva_to_raw(pe, start_rva)
        if off is None:
            print("  no raw mapping")
            continue
        code = data[off: off + 0x180]
        for insn in md.disasm(code, base + start_rva):
            mark = ""
            if insn.address == va:
                mark = "   <<< REF SITE"
            if insn.operands:
                op = insn.operands[0]
                if op.type == 2 and 0xDC9300 <= op.imm <= 0xDC9500:
                    soff = rva_to_raw(pe, op.imm - base)
                    if soff is not None:
                        s = data[soff: soff + 48].split(b"\x00")[0]
                        mark += '   ; "%s"' % s.decode(errors="replace")
            print("  %08X  %-20s %s %s%s" % (
                insn.address, insn.bytes.hex(), insn.mnemonic,
                insn.op_str, mark))
            if insn.address > va + 0x60:
                break


if __name__ == "__main__":
    main()
