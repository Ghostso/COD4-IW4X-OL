import os
import struct

import capstone
import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
SEARCH_ROOTS = [IIPS, os.path.join(IIPS, "Tenio"), r"COD OL\IIPS", os.path.join(r"COD OL\IIPS", "Tenio")]

TARGET_EXPORTS = ("GetComponentIDs", "CreateComponent", "SetDLLRegistry")


def find_export(pe, name):
    if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        return None
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if exp.name and exp.name.decode("ascii", "replace") == name:
            return exp.address
    return None


def read_int_array(pe, data, rva, count, width=4, limit=4096):
    """Read up to `count` integers from an RVA inside the image."""
    out = []
    try:
        off = pe.get_offset_from_rva(rva)
    except Exception:
        return out
    if off is None or off < 0 or off >= len(data):
        return out
    n = min(count, limit) if count > 0 else limit
    for i in range(n):
        p = off + i * width
        if p + width > len(data):
            break
        if width == 4:
            out.append(struct.unpack_from("<I", data, p)[0])
        else:
            out.append(struct.unpack_from("<H", data, p)[0])
    return out


def scan_immediates_near(data, va_off, window=0x400):
    """Disassemble around a function entry and collect 32-bit immediates."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    chunk = data[va_off:va_off + window]
    values = []
    for insn in md.disasm(chunk, 0):
        for op in insn.operands:
            if op.type == capstone.x86.X86_OP_IMM:
                values.append((hex(insn.address), insn.mnemonic, insn.op_str, op.imm & 0xFFFFFFFF))
    return values


def main():
    seen = {}
    for root in SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.lower().endswith(".dll"):
                continue
            path = os.path.join(root, name)
            if path in seen:
                continue
            seen[path] = True
            try:
                data = open(path, "rb").read()
                pe = pefile.PE(path, fast_load=True)
                pe.parse_data_directories(
                    directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
                )
            except Exception as e:
                continue
            has_factory = False
            for exp in TARGET_EXPORTS:
                if find_export(pe, exp) is not None:
                    has_factory = True
            if not has_factory:
                continue

            print("=" * 78)
            rel = path.replace(r"run_codol_001\sandbox_ifs1_20260923\\", "").replace(r"COD OL\\", "ORIG/")
            print(rel, os.path.getsize(path))

            gci = find_export(pe, "GetComponentIDs")
            if gci is not None:
                try:
                    off = pe.get_offset_from_rva(gci)
                    print("  GetComponentIDs RVA=0x%X off=0x%X" % (gci, off))
                    imms = scan_immediates_near(data, off, 0x300)
                    printed = 0
                    for addr, mn, ops, imm in imms:
                        if mn in ("push", "mov", "cmp") and 0 < imm < 100000:
                            print(f"    {addr} {mn} {ops}   (imm={imm})")
                            printed += 1
                        if printed > 60:
                            break
                except Exception as e:
                    print("  disasm error:", e)

            # Also scan the whole module for the immediate 985 in code-ish sections
            hits985 = []
            needle = struct.pack("<I", 985)
            start = 0
            while True:
                i = data.find(needle, start)
                if i < 0:
                    break
                hits985.append(i)
                start = i + 1
            if hits985:
                print("  raw LE-985 hits:", [hex(h) for h in hits985])


if __name__ == "__main__":
    main()
