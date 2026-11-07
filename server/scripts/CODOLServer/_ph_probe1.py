#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ProtocalHandler.dll static disassembly: SetKey / AES / RNG / call site."""

import os
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'Cross', 'ProtocalHandler.dll')

VA_SETKEY = 0x10063DF0
VA_AES_SETKEY = 0x10077E90
VA_KEYEXP = 0x10078258
VA_RNG = 0x100626C0
VA_CALLSITE = 0x10064DB0
VA_HELPER = 0x1007AA80


def main():
    d = open(DLL, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    print('DLL=%s size=%d imagebase=0x%08X entry=0x%08X'
          % (DLL, len(d), ib, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    secs = []
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        secs.append((nm, s.VirtualAddress, s.PointerToRawData,
                     s.SizeOfRawData))
        print('%-10s rva=%08X raw=%08X rawsz=%08X'
              % (nm, s.VirtualAddress, s.PointerToRawData,
                 s.SizeOfRawData))

    def va_to_off(va):
        rva = va - ib
        for nm, rv, raw, sz in secs:
            if rv <= rva < rv + sz:
                return raw + (rva - rv), nm
        return None, None

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    def disasm(va, n, label):
        off, nm = va_to_off(va)
        print('')
        print('=== %s  VA=%08X rva=%08X file_off=0x%X sec=%s ==='
              % (label, va, va - ib, off or 0, nm))
        if off is None:
            print('  NOT MAPPED')
            return
        data = d[off:off + n]
        for ins in md.disasm(data, va):
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))
            if ins.mnemonic == 'ret' and ins.address > va + 8:
                # do not stop for ret imm in OpenSSL helpers unless very near
                pass

    disasm(VA_SETKEY, 0x260, 'SetKey 0x10063DF0')
    disasm(VA_AES_SETKEY, 0x140, 'AES_set_encrypt_key 0x10077E90')
    disasm(VA_KEYEXP, 0x260, 'KeyExpansion 0x10078258')
    disasm(VA_RNG, 0x180, 'RNG 0x100626C0')
    disasm(VA_CALLSITE, 0x180, 'call site 0x10064DB0')
    disasm(VA_HELPER, 0x120, 'SetKey helper 0x1007AA80')

    print('')
    print('=== file offsets of key VAs ===')
    for va in (VA_SETKEY, VA_AES_SETKEY, VA_KEYEXP, VA_RNG,
               VA_CALLSITE, VA_HELPER):
        off, nm = va_to_off(va)
        print('  %08X -> %s:0x%X' % (va, nm, off or 0))


if __name__ == '__main__':
    main()
