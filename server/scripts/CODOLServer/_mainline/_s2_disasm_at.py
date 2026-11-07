# -*- coding: utf-8 -*-
"""S2-I: disassemble a VA window in a PE using capstone (static only)."""
import sys
import pefile
import capstone


def main():
    path = sys.argv[1]
    va = int(sys.argv[2], 0)
    before = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x80
    after = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x100
    pe = pefile.PE(path, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    rva = va - base
    sec = None
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            sec = s
            break
    if sec is None:
        raise SystemExit("VA not in a section")
    off = sec.PointerToRawData + (rva - sec.VirtualAddress)
    raw = open(path, "rb").read()
    start = max(0, off - before)
    end = min(len(raw), off + after)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    print("file=%s sec=%s va=%#x off=%#x" % (path, sec.Name.rstrip(b"\x00").decode(), va, off))
    for insn in md.disasm(raw[start:end], base + (start - sec.PointerToRawData + sec.VirtualAddress)):
        mark = " <== HERE" if insn.address <= va < insn.address + insn.size else ""
        print("%08x: %-24s %s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))


if __name__ == "__main__":
    main()
