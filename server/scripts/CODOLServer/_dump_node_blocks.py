# -*- coding: utf-8 -*-
"""把 DIRTREERESP 的节点块按偏移逐字节展开，输出到 UTF-8 文本。

只读分析工具。
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
RSP = os.path.join(HERE, 'tcls_dirtree_response.bin')
OUT = os.path.join(HERE, '_tcls_blocks.txt')

HEAD_LEN = 26


def hexrow(data, base=0, width=16):
    rows = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        rows.append('  %04x  %-48s  %s' % (
            base + off,
            ' '.join('%02x' % b for b in chunk),
            ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)))
    return rows


def main():
    d = open(RSP, 'rb').read()
    payload = d[HEAD_LEN:]
    lines = []
    lines.append('total=%d head=%d payload=%d' % (len(d), HEAD_LEN, len(payload)))
    lines.append('')

    lines.append('== 完整 hexdump（含 ASCII 列） ==')
    lines.extend(hexrow(d))
    lines.append('')

    lines.append('== www.qq.com 出现点前后 24 字节 ==')
    for pos in [384, 415, 494, 525, 604, 635, 715, 746]:
        lines.append('  pos=%d' % pos)
        lines.extend(hexrow(d[max(0, pos - 24):pos + 40], base=max(0, pos - 24)))
        lines.append('')

    lines.append('== 逐 u32be 扫描（前 96 字节） ==')
    for off in range(0, min(96, len(d) - 4), 4):
        v = struct.unpack_from('>I', d, off)[0]
        lines.append('  off=%-3d u32be=%-12d 0x%08X' % (off, v, v))
    lines.append('')

    lines.append('== dir_root 之后逐 u32be（偏移 40..200） ==')
    for off in range(40, 200, 4):
        v = struct.unpack_from('>I', d, off)[0]
        lines.append('  off=%-3d u32be=%-12d 0x%08X' % (off, v, v))

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
