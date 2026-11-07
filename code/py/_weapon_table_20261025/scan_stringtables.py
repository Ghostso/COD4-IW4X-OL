# -*- coding: utf-8 -*-
"""Scan type-37 (stringtable) assets in an inflated CODOL zone and dump their headers."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
DIR_OFF, DIR_COUNT = 0xFC24, 8557
ASSET_BASE = 0x28


def main():
    d = open(ZONE, 'rb').read()
    print('zone size', len(d))
    n = 0
    for i in range(DIR_COUNT):
        typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
        if typ != 37:
            continue
        n += 1
        base = ASSET_BASE + off
        blob = d[base:base + min(size, 64)]
        head = ' '.join('%02x' % c for c in blob[:32])
        # printable runs in the first 128 bytes
        chunk = d[base:base + min(size, 256)]
        runs = []
        cur = b''
        for c in chunk:
            if 32 <= c < 127:
                cur += bytes([c])
            else:
                if len(cur) >= 3:
                    runs.append(cur.decode('latin-1'))
                cur = b''
        if len(cur) >= 3:
            runs.append(cur.decode('latin-1'))
        print(i, hex(off), size, head, runs[:4])
    print('type37 total', n)


if __name__ == '__main__':
    main()
