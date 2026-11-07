# -*- coding: utf-8 -*-
"""
_po4_disasm_host.py - static disassembly helper for the IIPS host chain.

Read-only.  Resolves IAT slots for a set of Win32 APIs inside a module and
prints every xref (E8 rel32 call / FF15 indirect call / push imm) together
with a short capstone window, so the ordering question
"is the named pipe created before or after the Tenio/TPF UI init?"
can be answered from the binary instead of from a live run.

Usage:
    python -X utf8 _po4_disasm_host.py IIPSHostApp.exe GetCommandLineW ...
    python -X utf8 _po4_disasm_host.py IIPSHost.dll CreateNamedPipeA ...
"""
import os
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
IIPS = os.path.join(ROOT, 'COD OL', 'IIPS')


def iat_slots(pe, image_base, names):
    """Return {api_name: absolute IAT VA} for the requested import names."""
    out = {}
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in entry.imports:
            if not imp.name:
                continue
            nm = imp.name.decode('ascii', 'replace')
            if nm in names:
                out.setdefault(nm, imp.address)
    return out


def section_of(pe, va):
    image_base = pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        lo = image_base + s.VirtualAddress
        hi = lo + max(s.Misc_VirtualSize, s.SizeOfRawData)
        if lo <= va < hi:
            return s
    return None


def va_to_off(pe, image_base, va):
    s = section_of(pe, va)
    if not s:
        return None
    return s.PointerToRawData + (va - (image_base + s.VirtualAddress))


def text_blob(pe, image_base):
    """Return (blob, base_va, ranges) covering all executable sections."""
    ranges = []
    chunks = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        base = image_base + s.VirtualAddress
        size = s.SizeOfRawData
        raw = s.get_data()
        if len(raw) < size:
            size = len(raw)
        ranges.append((base, base + size))
    return ranges


def find_xrefs(pe, image_base, target_va):
    """Find call/jmp/push xrefs to target_va inside executable sections."""
    hits = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        base = image_base + s.VirtualAddress
        raw = s.get_data()
        # E8/E9 rel32
        for i in range(len(raw) - 5):
            op = raw[i]
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from('<i', raw, i + 1)[0]
                src = base + i
                if (src + 5 + rel) & 0xFFFFFFFF == target_va:
                    hits.append((src, 'rel32-' + ('call' if op == 0xE8 else 'jmp')))
        # FF15 [imm32]  (indirect call through IAT)
        for i in range(len(raw) - 6):
            if raw[i] == 0xFF and raw[i + 1] == 0x15:
                imm = struct.unpack_from('<I', raw, i + 2)[0]
                if imm == target_va:
                    hits.append((base + i, 'call[mem]'))
        # 68 imm32 (push)
        for i in range(len(raw) - 5):
            if raw[i] == 0x68:
                imm = struct.unpack_from('<I', raw, i + 1)[0]
                if imm == target_va:
                    hits.append((base + i, 'push'))
    return hits


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.join(IIPS, path)
    rest = sys.argv[2:]

    pe0 = pefile.PE(path, fast_load=False)
    base0 = pe0.OPTIONAL_HEADER.ImageBase
    md0 = Cs(CS_ARCH_X86, CS_MODE_32)

    if rest and rest[0] == '--dump':
        va = int(rest[1], 0)
        n = int(rest[2], 0) if len(rest) > 2 else 0x80
        img = pe0.get_memory_mapped_image()
        print('module %s  base 0x%08X  dump 0x%08X..0x%08X'
              % (path, base0, va, va + n))
        for ins in md0.disasm(img[va - base0:va - base0 + n], va):
            print('  0x%08X  %-24s %s %s'
                  % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        return 0

    if rest and rest[0] == '--callers':
        target = int(rest[1], 0)
        hits = []
        for s in pe0.sections:
            if not (s.Characteristics & 0x20000000):
                continue
            b = base0 + s.VirtualAddress
            raw = s.get_data()
            for i in range(len(raw) - 5):
                if raw[i] in (0xE8, 0xE9):
                    rel = struct.unpack_from('<i', raw, i + 1)[0]
                    src = b + i
                    if (src + 5 + rel) & 0xFFFFFFFF == target:
                        hits.append((src, 'call' if raw[i] == 0xE8 else 'jmp'))
        print('module %s  callers of 0x%08X : %d' % (path, target, len(hits)))
        for src, k in hits:
            print('   %-4s 0x%08X' % (k, src))
        return 0

    apis = rest

    pe = pefile.PE(path, fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print('module    : %s' % path)
    print('imagebase : 0x%08X' % image_base)
    print('entry     : 0x%08X' % (image_base + pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print('')

    slots = iat_slots(pe, image_base, set(apis))
    for name in apis:
        va = slots.get(name)
        if va is None:
            print('%-28s : not imported' % name)
            continue
        hits = find_xrefs(pe, image_base, va)
        print('%-28s : IAT 0x%08X   xrefs %d' % (name, va, len(hits)))
        for src, kind in hits[:14]:
            off = va_to_off(pe, image_base, src)
            print('    %s 0x%08X' % (kind, src))
            for ins in md.disasm(pe.get_memory_mapped_image()[src - image_base:
                                                               src - image_base + 0x30],
                                 src):
                print('        0x%08X  %-24s %s %s'
                      % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
