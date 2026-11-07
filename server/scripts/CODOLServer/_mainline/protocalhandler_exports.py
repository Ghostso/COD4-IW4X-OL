#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List exports + AES-related call sites in ProtocalHandler.dll."""

import struct
import pefile
import capstone

PATH = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'


def main():
    pe = pefile.PE(PATH, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
                                           pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    print('=== exports ===')
    try:
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            print('  ord=%d rva=%08X va=%08X %s' %
                  (e.ordinal, e.address, ib + e.address,
                   e.name.decode() if e.name else ''))
    except Exception as exc:
        print('  no exports:', exc)

    print('\n=== imports ===')
    try:
        for d in pe.DIRECTORY_ENTRY_IMPORT:
            names = [i.name.decode() if i.name else str(i.ordinal)
                     for i in d.imports[:25]]
            print('  %s: %s' % (d.dll.decode(), ', '.join(names)))
    except Exception as exc:
        print('  no imports:', exc)

    data = open(PATH, 'rb').read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    text = None
    for s in pe.sections:
        if s.Name.decode(errors='replace').startswith('.text'):
            text = s
    start = text.PointerToRawData
    sec = data[start:start + text.SizeOfRawData]
    # find function prologues that call the AES routine region
    aes_probe = struct.pack('<I', ib + 0x7A44F)
    print('\n=== callers referencing the AES table area ===')
    n = 0
    for i in range(0, len(sec) - 4):
        if sec[i:i + 4] == aes_probe:
            n += 1
            if n <= 10:
                print('  hit at rva=%08X' % (text.VirtualAddress + i))
    print('total refs to 0x1007A44F: %d' % n)


if __name__ == '__main__':
    main()
