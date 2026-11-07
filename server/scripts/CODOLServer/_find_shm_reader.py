# -*- coding: utf-8 -*-
"""Locate the code that opens/reads TCLS_SHAREDMEMEMORY<pid>.

Strategy:
  1. Find the ASCII string 'TCLS_SHAREDMEMEMORY' in codoMP_client_shipRetailBase.dll
     and the UTF-16 literal 'TCLS_TASMEMORY_'.
  2. Find its VA, then scan .text for instructions that push/reference that VA
     (i.e. `push imm32` = 0x68 <va>, or `mov r32, imm32` = 0xB8+r <va>).
  3. Report the containing function boundaries so we can disassemble it.

Read-only. Writes nothing except the report.
"""
import os
import struct

import pefile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(HERE, '_shm_reader_xrefs.txt')

TARGETS = [
    (b'TCLS_SHAREDMEMEMORY', 'ascii'),
    (b'T\0C\0L\0S\0_\0T\0A\0S\0M\0E\0M\0O\0R\0Y\0_\0', 'utf16'),
    (b'TAS-3AAC03A5-7D57-4c80-A175-0E4BEA43EE41-%u', 'ascii'),
]


def main():
    dll = os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
    pe = pefile.PE(dll, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    data = open(dll, 'rb').read()
    lines = []
    lines.append('module: %s' % dll)
    lines.append('imagebase: 0x%08X' % base)
    lines.append('')

    text = None
    for s in pe.sections:
        name = s.Name.rstrip(b'\x00').decode('ascii', 'replace')
        if name == '.text':
            text = s
        lines.append('section %-10s raw=0x%06X vsize=0x%06X rva=0x%06X' % (
            name, s.PointerToRawData, s.Misc_VirtualSize, s.VirtualAddress))
    lines.append('')

    def raw_to_va(off):
        for s in pe.sections:
            if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                return base + s.VirtualAddress + (off - s.PointerToRawData)
        return None

    for pat, kind in TARGETS:
        pos = 0
        while True:
            pos = data.find(pat, pos)
            if pos < 0:
                break
            va = raw_to_va(pos)
            lines.append('string %-14s off=0x%06X va=%s' % (
                kind, pos, ('0x%08X' % va) if va else 'n/a'))
            if va:
                imm = struct.pack('<I', va)
                hits = []
                for form, tag in ((b'\x68' + imm, 'push'),):
                    p = 0
                    while True:
                        p = data.find(form, p)
                        if p < 0:
                            break
                        hits.append((tag, p))
                        p += 1
                # mov r32, imm32 (B8..BF)
                for reg in range(8):
                    form = bytes([0xB8 + reg]) + imm
                    p = 0
                    while True:
                        p = data.find(form, p)
                        if p < 0:
                            break
                        hits.append(('mov r%d' % reg, p))
                        p += 1
                # also scan inside .text only for sanity
                if text:
                    tstart = text.PointerToRawData
                    tend = tstart + text.SizeOfRawData
                    hits = [h for h in hits if tstart <= h[1] < tend]
                for tag, off in hits:
                    lines.append('    xref %-8s file=0x%06X va=%s' % (
                        tag, off, ('0x%08X' % (raw_to_va(off) or 0))))
            pos += 1
        lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
