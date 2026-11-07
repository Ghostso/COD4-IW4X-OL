# -*- coding: utf-8 -*-
"""Find references to TCLS_SHAREDMEMEMORY via the PE relocation table.

The plain push/mov scan found nothing, so the address must be materialised via
a relocatable pointer stored in .data/.rdata. This walks IMAGE_REL_BASED_HIGHLOW
entries and reports every reloc site whose *content* equals the target VA, plus
the section it lives in.

Read-only.
"""
import os
import struct

import pefile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(HERE, '_shm_reader_relocs.txt')

TARGET_VA = 0x1088FFFC          # 'TCLS_SHAREDMEMEMORY'
TARGET_VA_UTF16 = 0x1089013C    # 'TCLS_TASMEMORY_' (utf16)


def main():
    dll = os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
    pe = pefile.PE(dll)
    base = pe.OPTIONAL_HEADER.ImageBase
    data = open(dll, 'rb').read()
    lines = []
    lines.append('imagebase 0x%08X' % base)
    lines.append('target(s): 0x%08X, 0x%08X' % (TARGET_VA, TARGET_VA_UTF16))
    lines.append('')

    def va_to_raw(va):
        rva = va - base
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(
                    s.Misc_VirtualSize, s.SizeOfRawData):
                off = s.PointerToRawData + (rva - s.VirtualAddress)
                if off < len(data):
                    return off, s
        return None, None

    want = {TARGET_VA, TARGET_VA_UTF16}
    found = 0
    for block in getattr(pe, 'DIRECTORY_ENTRY_BASERELOC', []):
        for entry in block.entries:
            if entry.type != 3:          # IMAGE_REL_BASED_HIGHLOW
                continue
            site_va = base + entry.rva
            off, sec = va_to_raw(site_va)
            if off is None or off + 4 > len(data):
                continue
            value = struct.unpack_from('<I', data, off)[0]
            if value in want:
                secname = sec.Name.rstrip(b'\x00').decode('ascii', 'replace')
                lines.append('reloc site va=0x%08X in %-8s -> points to 0x%08X' % (
                    site_va, secname, value))
                found += 1
    lines.append('')
    lines.append('total reloc sites pointing at targets: %d' % found)

    # Also: how many HIGHLOW relocs exist in total (sanity).
    total = sum(1 for b in getattr(pe, 'DIRECTORY_ENTRY_BASERELOC', [])
                for e in b.entries if e.type == 3)
    lines.append('total HIGHLOW relocs: %d' % total)

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
