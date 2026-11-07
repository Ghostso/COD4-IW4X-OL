import os

import capstone
import pefile

CROSS_TPF = r"COD OL\Cross\Tenio\TenTPF.dll"
IIPS_TPF = r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenTPF.dll"
OFFSETS = [0xBE8B7, 0xBEBA5]


def hexdump(data, start, end):
    for off in range(start, end, 16):
        chunk = data[off:off + 16]
        hx = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("      %08x  %-47s  %s" % (off, hx, asc))


def disasm(path, offsets, window_before=64, window_after=96):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    data = open(path, "rb").read()
    pe = pefile.PE(path, fast_load=True)
    print("=" * 96)
    print(path)
    print("  size=%d  PE_ts=%d" % (len(data), pe.FILE_HEADER.TimeDateStamp))

    for hit in offsets:
        rva = pe.get_rva_from_offset(hit)
        sec = pe.get_section_by_rva(rva) if rva is not None else None
        secname = sec.Name.decode("ascii", "replace").strip("\x00") if sec else "?"
        print("-" * 90)
        print("  file_off=0x%X rva=%s section=%s" % (
            hit, ("0x%X" % rva) if rva is not None else "?", secname))
        start = max(0, hit - window_before)
        end = min(len(data), hit + window_after)
        hexdump(data, start, end)
        print("      --- disassembly ---")
        base = (rva - window_before) if rva is not None else (hit - window_before)
        for insn in md.disasm(data[start:end], max(0, base)):
            mark = ""
            if rva is not None and insn.address <= rva < insn.address + insn.size:
                mark = "   <=== 0x3d9 = 985"
            print("      %08x  %-12s %s%s" % (insn.address, insn.mnemonic, insn.op_str, mark))


def compare_exports():
    print("=" * 96)
    print("Export comparison")
    for path in (CROSS_TPF, IIPS_TPF):
        if not os.path.exists(path):
            print("  MISSING", path)
            continue
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
        entry = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
        names = []
        if entry is not None and not isinstance(entry, list):
            for exp in getattr(entry, "symbols", []):
                if exp.name:
                    names.append(exp.name.decode("ascii", "replace"))
        print(f"  {path}")
        print(f"    size={os.path.getsize(path)} exports={names}")


if __name__ == "__main__":
    if os.path.exists(CROSS_TPF):
        disasm(CROSS_TPF, OFFSETS)
    else:
        print("MISSING", CROSS_TPF)
    compare_exports()
