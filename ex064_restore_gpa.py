# EX-064 TASK C/D/H/K: locate the dynamic GetProcAddress path in
# IIPSLaunchRestore.dll that resolves "GetResourceManagerII".
import json
from collections import OrderedDict

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


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

    def is_code(self, rva):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if ch & 0x20000000 and va <= rva < va + max(vs, rs):
                return True
        return False

    def codesec(self):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if ch & 0x20000000:
                return va, va + vs
        return 0x1000, 0x1000


def push_refs(img, va):
    """Find `push imm32` instructions whose immediate == va."""
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    lo, hi = img.codesec()
    out = []
    rva = lo
    while rva < hi:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        if insn.mnemonic == "push" and insn.operands \
                and insn.operands[0].type == X86_OP_IMM \
                and insn.operands[0].imm == va:
            out.append(rva)
        rva += insn.size
    return out


def main():
    img = Img(RESTORE)
    print("=" * 78)
    print("IIPSLaunchRestore.dll  base 0x%X  size 0x%X" % (
        img.base, img.size))
    print("=" * 78)
    for nm, va, vs, raw, rs, ch in img.secs:
        print("  %-10s VA 0x%08X vsize 0x%07X raw 0x%06X rawsize 0x%07X ch %08X"
              % (nm, va, vs, raw, rs, ch))

    print()
    print("IAT slots of LoadLibraryA / LoadLibraryW / GetProcAddress:")
    for slot, (dll, name) in sorted(img.imports.items()):
        if name in ("LoadLibraryA", "LoadLibraryW", "GetProcAddress",
                    "LoadLibraryExA", "LoadLibraryExW"):
            print("   0x%X  %s!%s" % (img.base + slot, dll, name))

    print()
    print("=" * 78)
    print("push-references to the export-name strings")
    print("=" * 78)
    for name, va in (("GetResourceManagerII", 0x1006F43C),
                     ("ReleaseResourceManagerII", 0x1006F454)):
        refs = push_refs(img, va)
        print("  %-26s VA 0x%X  push-refs: %s" % (
            name, va, ["0x%X" % r for r in refs] or "NONE"))

    print()
    print("=" * 78)
    print("all lea/mov references to the name strings (any form)")
    print("=" * 78)
    data = img.data
    for name, va in (("GetResourceManagerII", 0x1006F43C),
                     ("ReleaseResourceManagerII", 0x1006F454)):
        needle = va.to_bytes(4, "little")
        st = 0
        hits = []
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            hits.append(i)
            st = i + 1
        print("  %-26s le32 occurrences in file: %d" % (name, len(hits)))
        for h in hits:
            for (nm, sva, vs, raw, rs, ch) in img.secs:
                if raw <= h < raw + rs:
                    print("       raw 0x%X  RVA 0x%X  sec %s" % (
                        h, sva + (h - raw), nm))
                    break


if __name__ == "__main__":
    main()
