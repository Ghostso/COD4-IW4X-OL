#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate AES S-boxes and QoS/key-related strings in platform binaries."""

import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
FILES = [
    r'tqm\TQMCenter.exe',
    r'tqm\SSOPlatform.dll',
    r'tqm\SSOCommon.dll',
    r'IIPS\IIPSHostApp.exe',
    r'IIPS\IIPSHost.dll',
    r'IIPS\iips.dll',
    r'IIPS\p2papp.dll',
    r'IIPS\Tenio\ScriptManager.dll',
    r'Cross\CrossProxy.exe',
    r'Cross\CrossShell.dll',
    r'Cross\SSOPlatform.dll',
    r'Cross\ProtocalHandler.dll',
    r'Cross\Tenio\June.dll',
]

INV_SBOX = bytes.fromhex(
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

TERMS = [b'qos', b'tqos', b'8081', b'gamesafe', b'ticket', b'iv_seed',
         b'AES', b'aes', b'ECB', b'QOSCSPkg', b'qos_cs', b'qos_ss']


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'PLATFORM_AES_SCAN.md')
    lines = ['# Platform AES / QoS scan', '']
    for rel in FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            continue
        data = open(p, 'rb').read()
        sbox = [i for i in range(len(data)) if data.startswith(INV_SBOX, i)]
        hits = {}
        for t in TERMS:
            n = data.count(t)
            if n:
                hits[t.decode('ascii', 'replace')] = n
        lines.append('## %s (%d bytes)' % (rel, len(data)))
        lines.append('- AES inv S-box offsets: %s' %
                     (', '.join('0x%X' % x for x in sbox[:8]) or 'none'))
        lines.append('- term hits: %s' % (hits or 'none'))
        lines.append('')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
