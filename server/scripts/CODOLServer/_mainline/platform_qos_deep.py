#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep read of QoS-related strings/structures in platform DLLs."""

import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
TARGETS = [r'Cross\ProtocalHandler.dll', r'Cross\CrossShell.dll',
           r'IIPS\IIPSHost.dll', r'IIPS\iips.dll', r'IIPS\p2papp.dll',
           r'tqm\SSOPlatform.dll']

TERMS = [b'qos_cs', b'qos_ss', b'QOSCSPkg', b'QOS_CS', b'QOS_SS',
         b'GAMESVR', b'GameSvrIPList', b'ConndIPPortList', b'MAGIC',
         b'8081', b'tqos', b'QOS_GET', b'QOS_REP', b'QOS_SPDTST',
         b'ru', b'su', b'key', b'Key', b'iv', b'ticket']


def printable(b):
    return ''.join(chr(c) if 32 <= c < 127 else '.' for c in b)


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'PLATFORM_QOS_DEEP.txt')
    with open(out, 'w', encoding='utf-8', errors='replace') as fh:
        for rel in TARGETS:
            p = os.path.join(ROOT, rel)
            if not os.path.isfile(p):
                continue
            data = open(p, 'rb').read()
            fh.write('\n########## %s (%d bytes)\n' % (rel, len(data)))
            for t in TERMS:
                offs = [m.start() for m in re.finditer(re.escape(t), data)]
                if not offs:
                    continue
                fh.write('\n=== term %s hits=%d\n' % (t.decode('ascii', 'replace'), len(offs)))
                for o in offs[:12]:
                    lo = max(0, o - 96)
                    hi = min(len(data), o + 160)
                    fh.write('  off=0x%X\n' % o)
                    fh.write('    %s\n' % printable(data[lo:hi]))
    print('wrote', out)


if __name__ == '__main__':
    main()
