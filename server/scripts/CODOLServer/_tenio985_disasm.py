import os
import struct

import capstone
import pefile

TARGETS = [
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenTPF.dll", [0x1B9C77, 0x1BA755, 0x26A9D8, 0x2704D0]),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\June.dll", [0x69713]),
]


def hexdump(data, start, end):
    for off in range(start, end, 16):
        chunk = data[off:off + 16]
        hx = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("    %08x  %-47s  %s" % (off, hx, asc))


def main():
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    for path, offsets in TARGETS:
        print("=" * 90)
        print(path)
        data = open(path, "rb").read()
        pe = pefile.PE(path, fast_load=True)
        for hit in offsets:
            rva = pe.get_rva_from_offset(hit)
            sec = pe.get_section_by_rva(rva) if rva is not None else None
            print("-" * 80)
            print("file_off=0x%X rva=%s section=%s" % (
                hit,
                ("0x%X" % rva) if rva is not None else "?",
                sec.Name.decode("ascii", "replace").strip("\x00") if sec else "?",
            ))
            start = max(0, hit - 40)
            end = min(len(data), hit + 56)
            hexdump(data, start, end)
            print("    --- disassembly around hit ---")
            try:
                base_addr = rva - 40 if rva is not None else hit - 40
                for insn in md.disasm(data[start:end], max(0, base_addr)):
                    marker = " <== 985" if insn.address <= (rva or 0) < insn.address + insn.size else ""
                    print("      %08x  %-10s %s%s" % (insn.address, insn.mnemonic, insn.op_str, marker))
            except Exception as e:
                print("      disasm error:", e)


if __name__ == "__main__":
    main()
