#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find function start + callers of the AES routine inside ProtocalHandler.dll."""

import struct
import pefile
import capstone

PATH = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
ANCHOR_RVA = 0x7A44F


def main():
    pe = pefile.PE(PATH, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    data = open(PATH, 'rb').read()

    def rva2fo(rva):
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + s.SizeOfRawData:
                return s.PointerToRawData + (rva - s.VirtualAddress)
        return None

    fo = rva2fo(ANCHOR_RVA)
    start = fo
    for i in range(fo, max(0, fo - 0x300), -1):
        if data[i:i + 2] == b'\x55\x8b':  # push ebp; mov ebp,...
            start = i
            break
    start_rva = pe.sections[0].VirtualAddress + (start - pe.sections[0].PointerToRawData) \
        if pe.sections[0].PointerToRawData <= start < pe.sections[0].PointerToRawData + pe.sections[0].SizeOfRawData \
        else ANCHOR_RVA
    print('anchor rva=%08X fo=%X  func_start fo=%X rva=%08X' %
          (ANCHOR_RVA, fo, start, start_rva))

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    print('\n=== prelude ===')
    for ins in md.disasm(data[start:start + 96], ib + start_rva):
        print('  %08X %-20s %s %s' %
              (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))

    target = ib + start_rva
    callers = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        sec = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        for i in range(len(sec) - 5):
            if sec[i] != 0xE8:
                continue
            rel = struct.unpack_from('<i', sec, i + 1)[0]
            src_rva = s.VirtualAddress + i
            dst = ib + src_rva + 5 + rel
            if dst == target:
                callers.append(src_rva)
    print('\ncallers of %08X: %s' % (target, ['%08X' % c for c in callers]))

    for c in callers[:10]:
        cfo = rva2fo(c)
        lo = max(0, cfo - 96)
        print('\n=== caller rva=%08X ===' % c)
        for ins in md.disasm(data[lo:cfo + 64], ib + (c - (cfo - lo))):
            print('  %08X %-20s %s %s' %
                  (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))


if __name__ == '__main__':
    main()
