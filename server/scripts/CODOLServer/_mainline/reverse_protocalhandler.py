#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reverse the plaintext platform QoS implementation in ProtocalHandler.dll."""

import struct
import pefile
import capstone

PATH = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
INV_SBOX_OFF = 0xDC0B4


def main():
    pe = pefile.PE(PATH, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    print('machine=%X imagebase=%08X entry=%08X' %
          (pe.FILE_HEADER.Machine, ib, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    for s in pe.sections:
        n = s.Name.decode(errors='replace').strip('\x00')
        print('  %-10s VA=%08X VS=%X RAW=%X PTR=%X X=%s' %
              (n, s.VirtualAddress, s.Misc_VirtualSize, s.SizeOfRawData,
               s.PointerToRawData, bool(s.Characteristics & 0x20000000)))

    def fo2rva(fo):
        for s in pe.sections:
            if s.PointerToRawData <= fo < s.PointerToRawData + s.SizeOfRawData:
                return s.VirtualAddress + (fo - s.PointerToRawData)
        return None

    sbox_va = ib + fo2rva(INV_SBOX_OFF)
    print('inv_sbox VA=%08X' % sbox_va)

    data = open(PATH, 'rb').read()
    needle = struct.pack('<I', sbox_va)
    refs = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        start = s.PointerToRawData
        end = start + s.SizeOfRawData
        sec = data[start:end]
        i = 0
        while True:
            i = sec.find(needle, i)
            if i < 0:
                break
            refs.append((s.VirtualAddress + i, start + i))
            i += 1
    print('absolute sbox refs=%d' % len(refs))

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for rva, fo in refs[:20]:
        lo = max(0, fo - 48)
        chunk = data[lo:fo + 64]
        print('\n=== ref rva=%08X va=%08X' % (rva, ib + rva))
        for ins in md.disasm(chunk, ib + (rva - (fo - lo))):
            print('  %08X %-20s %s %s' %
                  (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))

    for tok in (b'qos_cs\x00', b'qos_ss\x00', b'AES', b'QOS_CS_MAGIC',
                b'QOS_SS_MAGIC', b'ru\x00\x00\x00', b'su\x00\x00\x00'):
        offs = []
        start = 0
        while True:
            i = data.find(tok, start)
            if i < 0:
                break
            offs.append(i)
            start = i + 1
        print('\nTOKEN %r offs=%s' %
              (tok, ['0x%X' % o for o in offs[:20]]))
        for o in offs[:10]:
            va = ib + fo2rva(o) if fo2rva(o) is not None else None
            print('  off=%X va=%s ctx=%r' %
                  (o, ('%08X' % va) if va else '?', data[o:o + 48]))


if __name__ == '__main__':
    main()
