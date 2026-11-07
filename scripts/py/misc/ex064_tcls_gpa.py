# EX-064 TASK I/K: locate the tcls_core.exe GetProcAddress site for
# "CreateIIPSRepair" and the LoadLibrary target it uses.
import json

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

TCLS = r"WeGame\tcls\tcls_core.exe"


class Img:
    def __init__(self, path):
        self.pe = pefile.PE(path, fast_load=True)
        self.pe.parse_data_directories()
        self.data = open(path, "rb").read()
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.by_rva = bytearray(self.size)
        self.secs = []
        for s in self.pe.sections:
            self.secs.append((s.Name.decode(errors="replace").rstrip("\x00"),
                              s.VirtualAddress, s.Misc_VirtualSize,
                              s.PointerToRawData, s.SizeOfRawData,
                              s.Characteristics))
            n = min(s.Misc_VirtualSize, s.SizeOfRawData)
            self.by_rva[s.VirtualAddress:s.VirtualAddress + n] = \
                self.data[s.PointerToRawData:s.PointerToRawData + n]
        self.imports = {}
        for d in self.pe.DIRECTORY_ENTRY_IMPORT:
            for i in d.imports:
                nm = i.name.decode() if i.name else "ord%d" % i.ordinal
                self.imports[i.address - self.base] = (d.dll.decode(), nm)

    def read(self, rva, n):
        return bytes(self.by_rva[rva:rva + n])

    def codesec(self):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if ch & 0x20000000:
                return va, va + vs
        return 0x1000, 0x1000

    def raw2rva(self, off):
        for (nm, sva, vs, raw, rs, ch) in self.secs:
            if raw <= off < raw + rs:
                return sva + (off - raw), nm
        return None, None


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("IAT slots of interest in tcls_core.exe")
    print("=" * 78)
    for slot, (dll, nm) in sorted(img.imports.items()):
        if nm in ("LoadLibraryA", "LoadLibraryW", "GetProcAddress",
                  "LoadLibraryExA", "LoadLibraryExW"):
            print("   0x%08X  %s!%s" % (img.base + slot, dll, nm))

    print()
    print("=" * 78)
    print("push-references to CreateIIPSRepair / RealeaseIIPSRepair strings")
    print("=" * 78)
    rva1, sec1 = img.raw2rva(0x1692B0)
    rva2, sec2 = img.raw2rva(0x1692C4)
    print("   CreateIIPSRepair    raw 0x1692B0 -> RVA 0x%X VA 0x%X sec %s"
          % (rva1, img.base + rva1, sec1))
    print("   RealeaseIIPSRepair  raw 0x1692C4 -> RVA 0x%X VA 0x%X sec %s"
          % (rva2, img.base + rva2, sec2))

    lo, hi = img.codesec()
    for nm, va in (("CreateIIPSRepair", img.base + rva1),
                   ("RealeaseIIPSRepair", img.base + rva2)):
        refs = []
        r = lo
        while r < hi:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                r += 1
                continue
            if insn.mnemonic == "push" and insn.operands \
                    and insn.operands[0].type == X86_OP_IMM \
                    and insn.operands[0].imm == va:
                refs.append(r)
            r += insn.size
        print()
        print("   %s push-refs: %s" % (
            nm, ["0x%X" % x for x in refs] or "NONE"))
        for site in refs:
            print()
            print("   --- context around 0x%X ---" % site)
            r = site - 0x50
            while r <= site + 0x50:
                insn = next(md.disasm(img.read(r, 16), img.base + r), None)
                if insn is None:
                    r += 1
                    continue
                mark = ""
                if insn.mnemonic == "call" and insn.operands:
                    op = insn.operands[0]
                    if op.type == X86_OP_MEM and op.mem.base == 0:
                        n = img.imports.get(op.mem.disp - img.base)
                        if n:
                            mark = "   ; %s!%s" % n
                    elif op.type == X86_OP_IMM:
                        mark = "   ; -> sub_%X" % (op.imm - img.base)
                if insn.operands and insn.operands[0].type == X86_OP_IMM:
                    t = insn.operands[0].imm - img.base
                    if 0 <= t < img.size:
                        s = img.read(t, 80).split(b"\x00")[0]
                        if len(s) >= 4 and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
                star = "   <<<" if r == site else ""
                print("     0x%05X  %-22s %s %s%s%s" % (
                    r, insn.bytes.hex(), insn.mnemonic, insn.op_str,
                    mark, star))
                r += insn.size


if __name__ == "__main__":
    main()
