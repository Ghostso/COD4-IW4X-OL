#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 7: find AES key-expansion / T-table / S-box code anywhere."""

import os
import re
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')

INV = bytes.fromhex(
    '52096ad53036a538bf40a39e81f3d7fb'
    '7ce339829b2fff87348e4344c4dee9cb'
    '547b9432a6c2233dee4c950b42fac34e'
    '082ea16628d924b2765ba2496d8bd125'
    '72f8f66486689816d4a45ccc5d65b692'
    '6c704850fdedb9da5e154657a78d9d84'
    '90d8ab008cbcd30af7e45805b8b34506'
    'd02c1e8fca3f0f02c1afbd0301138a6b'
    '3a9111414f67dcea97f2cfcef0b4e673'
    '96ac7422e7ad3585e2f937e81c75df6e'
    '47f11a711d29c5896fb7620eaa18be1b'
    'fc563e4bc6d279209adbc0fe78cd5af4'
    '1fdda8338807c731b11210592780ec5f'
    '60517fa919b54a0d2de57a9f93c99cef'
    'a0e03b4dae2af5b0c8ebbb3c83539961'
    '172b047eba77d626e169146355210c7d')

_fwd = bytearray(256)
for _i, _v in enumerate(INV):
    _fwd[_v] = _i
SBOX = bytes(_fwd)


def main():
    d = open(DLL, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    secs = [(s.Name.rstrip(b'\x00').decode('latin1'),
             s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections]

    def owner(off):
        for nm, rv, raw, sz in secs:
            if raw <= off < raw + sz:
                return nm, rv + (off - raw)
        return None, None

    print('=== whole-file byte searches ===')
    for name, pat in (('AES S-box', SBOX),
                      ('AES invS-box', INV),
                      ('AES Te0[0] c66363a5 LE', struct.pack('<I', 0xc66363a5)),
                      ('AES Te0[0] a5c66363 LE', struct.pack('<I', 0xa5c66363)),
                      ('rcon 01000000020000000400000008000000',
                       bytes.fromhex('01000000020000000400000008000000')),
                      ('AES_set_encrypt_key', b'AES_set_encrypt_key'),
                      ('AES_set_decrypt_key', b'AES_set_decrypt_key'),
                      ('EVP_EncryptInit', b'EVP_EncryptInit'),
                      ('EVP_DecryptInit', b'EVP_DecryptInit'),
                      ('Rijndael', b'Rijndael'),
                      ('aes_encrypt', b'aes_encrypt')):
        hits = []
        pos = 0
        while len(hits) < 20:
            i = d.find(pat, pos)
            if i < 0:
                break
            hits.append(i)
            pos = i + 1
        print('  %-38s %s' % (name,
                              ', '.join('%s@%08X' % owner(h)
                                        for h in hits)))

    print('')
    print('=== ASCII strings containing AES / crypto keywords ===')
    for m in re.finditer(rb'[ -~]{4,}', d):
        s = m.group()
        low = s.lower()
        if any(k in low for k in (b'aes', b'rijndael', b'evp_',
                                  b'crypt', b'sha256', b'hmac',
                                  b'set_encrypt', b'decryptinit')):
            nm, va = owner(m.start())
            print('  %-8s %08X  %r' % (nm, va, s[:100]))

    print('')
    print('=== disasm around any direct S-box/T-table hit ===')
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, pat in (('SBOX', SBOX), ('INV', INV)):
        i = d.find(pat)
        if i < 0:
            continue
        nm, va = owner(i)
        start = max(0, i - 64)
        print('--- %s at %s:%08X ---' % (name, nm, va))
        for ins in md.disasm(d[start:start + 160], va - 64):
            print('  %08X  %-8s %s' % (ins.address, ins.mnemonic,
                                       ins.op_str))


if __name__ == '__main__':
    main()
