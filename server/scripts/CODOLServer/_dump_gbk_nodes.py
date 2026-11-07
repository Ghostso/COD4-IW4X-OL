# -*- coding: utf-8 -*-
"""把 774 字节 DIRTREERESP 里的可读节点名（GBK/ASCII）全部列出来，写到 UTF-8 文件。

只读，不改动被抓包文件。
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
RSP = os.path.join(HERE, 'tcls_dirtree_response.bin')
OUT = os.path.join(HERE, '_tcls_nodes.txt')


def printable(s):
    return all(ch.isprintable() for ch in s)


def main():
    d = open(RSP, 'rb').read()
    lines = []
    lines.append('response len = %d' % len(d))
    lines.append('')

    lines.append('== 长度前缀候选（u8 / u16be / u32be），要求合法 GBK 且含汉字 ==')
    seen = []
    for plen in (1, 2, 4):
        for i in range(0, len(d) - plen):
            n = int.from_bytes(d[i:i + plen], 'big')
            if not (3 <= n <= 40):
                continue
            if i + plen + n > len(d):
                continue
            raw = d[i + plen:i + plen + n]
            try:
                s = raw.decode('gbk')
            except UnicodeDecodeError:
                continue
            if printable(s) and any('\u4e00' <= ch <= '\u9fff' for ch in s):
                key = (n, s)
                if key in seen:
                    continue
                seen.append(key)
                lines.append('  off=%-5d plen=%d len=%-3d %s' % (i, plen, n, s))

    lines.append('')
    lines.append('== ASCII 串 ==')
    cur = bytearray()
    start = None
    for i, b in enumerate(d):
        if 0x20 <= b < 0x7f:
            if start is None:
                start = i
            cur.append(b)
        else:
            if len(cur) >= 4:
                lines.append('  off=%-5d %s' % (start, cur.decode('ascii')))
            cur = bytearray()
            start = None
    if len(cur) >= 4:
        lines.append('  off=%-5d %s' % (start, cur.decode('ascii')))

    lines.append('')
    lines.append('== 头部字段 ==')
    lines.append('  magic            = %s' % d[:4].hex(' '))
    lines.append('  u32le @4 (len)   = %d' % struct.unpack_from('<I', d, 4)[0])
    svc = struct.unpack_from('>I', d, 8)[0]
    txn = struct.unpack_from('>I', d, 12)[0]
    lines.append('  u32be @8 (svc)   = %d (0x%08X)' % (svc, svc))
    lines.append('  u32be @12 (txn)  = %d (0x%08X)' % (txn, txn))
    lines.append('  u32be @16        = %d' % struct.unpack_from('>I', d, 16)[0])
    lines.append('  u16be @24        = 0x%04X' % struct.unpack_from('>H', d, 24)[0])
    lines.append('  u16be @26        = 0x%04X' % struct.unpack_from('>H', d, 26)[0])
    lines.append('  u16be @28        = 0x%04X' % struct.unpack_from('>H', d, 28)[0])
    lines.append('  u16be @30        = 0x%04X' % struct.unpack_from('>H', d, 30)[0])
    lines.append('  dir_root offset  = %d' % d.find(b'dir_root'))

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
