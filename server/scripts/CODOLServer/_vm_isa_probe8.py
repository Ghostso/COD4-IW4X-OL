#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 8: locate the AES key-expansion in the embedded libcrypto
and characterise .tvm0 as data (not a VM)."""

import os
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

    print('=== libcrypto build string ===')
    for pat in (b'openssl-0.9.8', b'OpenSSL 0.9', b'OpenSSL 1.',
                b'c:\\openssl'):
        pos = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            nm, va = owner(i)
            end = d.find(b'\x00', i)
            print('  %s@%08X  %r' % (nm, va, d[i:end][:120]))
            pos = i + 1

    print('')
    print('=== all AES invS-box copies (identifies crypto lib variants) ===')
    pos = 0
    while True:
        i = d.find(INV, pos)
        if i < 0:
            break
        nm, va = owner(i)
        print('  %s@%08X file_off=0x%X' % (nm, va, i))
        pos = i + 1

    print('')
    print('=== who references each invS-box copy? (absolute dword xref) ===')
    for i in range(len(d)):
        pass
    copies = []
    pos = 0
    while True:
        i = d.find(INV, pos)
        if i < 0:
            break
        copies.append(i)
        pos = i + 1
    for i in copies:
        nm, va = owner(i)
        # linked VA = ImageBase + rva
        linked = 0x10000000 + va
        pat = struct.pack('<I', linked)
        xr = []
        p2 = 0
        while len(xr) < 12:
            j = d.find(pat, p2)
            if j < 0:
                break
            xr.append(owner(j))
            p2 = j + 1
        print('  invS-box %s@%08X linked=%08X  xrefs=%s'
              % (nm, va, linked, xr))

    print('')
    print('=== AES key expansion signature scan ===')
    # ExpandKey for AES-128 (OpenSSL): uses rcon table and S-box byte loads.
    # Look for sequences referencing 4-byte rcon and doing 4 byte-rotations.
    for pat, label in (
            (bytes.fromhex('01000000020000000400000008000000'
                           '100000002000000040000000800000001b000000'),
             'openssl AES rcon[10] (LE dwords)'),
            (bytes.fromhex('01000000020000000400000008000000100000'
                           '00200000004000000080'),
             'rcon partial')):
        pos = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            print('  %-32s %s' % (label, owner(i)))
            pos = i + 1

    print('')
    print('=== AES_INIT_KEY string and surroundings ===')
    i = d.find(b'AES_INIT_KEY')
    if i >= 0:
        nm, va = owner(i)
        print('  %s@%08X' % (nm, va))
        start = max(0, i - 128)
        for k in range(0, 256, 16):
            row = d[start + k:start + k + 16]
            print('  %08X  %-47s  %s'
                  % (va - 128 + k, ' '.join('%02x' % c for c in row),
                     ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))

    print('')
    print('=== .tvm0 statistical character ===')
    tvm = next((rv, raw, sz) for nm, rv, raw, sz in secs if nm == '.tvm0')
    rv, raw, sz = tvm
    body = d[raw:raw + sz]
    print('  size=%d zeros=%d (%.2f%%)'
          % (len(body), body.count(0),
             100.0 * body.count(0) / len(body)))
    # opcode histogram of plausible x86 starts
    import collections
    c = collections.Counter(body[:1 << 20])
    print('  top bytes:', [(hex(k), v) for k, v in c.most_common(10)])
    # how often does 55 8B EC (push ebp; mov ebp,esp) appear?
    print('  55 8B EC (function prologue) count: %d'
          % body.count(b'\x55\x8b\xec'))
    print('  CC CC CC CC padding count: %d' % body.count(b'\xcc\xcc\xcc\xcc'))
    print('  E8 (call rel32) count: %d' % body.count(b'\xe8'))
    print('')
    print('  => a real x86 .text has thousands of 55 8B EC / CC padding.')
    print('     ratios are reported so the reader can judge.')

    print('')
    print('=== disasm at .tvm0 start (is it code?) ===')
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(body[:64], 0x10000000 + rv):
        print('  %08X  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))


if __name__ == '__main__':
    main()
