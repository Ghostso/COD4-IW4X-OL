"""完整解出 0x3AC62E5C 处的发送缓冲区。

已知该处是客户端拼好的 11/4 上行。往前找它的起点（找 "Player\0" 之前的字段），
往后找边界，然后按 tag 逐字段解析。

已知片段:
    ... 00 10 "Player" 00 13 08 a6 00 00 00 | 0a <roomId> 13 08 91 00 00 00 8d 00 00 00 | 02 04 ...

推测外层信封:
    08 <u32 service=11>  10 "Player\0"  13 08 <len> <payload>
这正好是 instant_push_body 的结构！
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')


def read(va, n):
    off = va - lo
    if off < 0:
        return None
    cov.seek(off)
    if cov.read(n) != b'\x01' * n:
        return None
    f.seek(off)
    d = f.read(n)
    return d if len(d) == n else None


ANCHOR = 0x3AC62E5C
back = 0x40
d = read(ANCHOR - back, back + 0x240)
if not d:
    print('不可读')
    raise SystemExit(1)

print('=== 0x%08X 起（含前 %d 字节） ===' % (ANCHOR - back, back))
for i in range(0, len(d), 16):
    va = ANCHOR - back + i
    chunk = d[i:i + 16]
    hexs = ' '.join('%02x' % c for c in chunk)
    asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
    mark = '  <<<' if va <= ANCHOR < va + 16 else ''
    print('  %08X  %-47s  %s%s' % (va, hexs, asc, mark))

print()
print('=== 从 0x%08X 之后的 tag 解析 ===' % ANCHOR)
p = d[back:]
i = 0
guard = 0
while i < len(p) - 1 and guard < 60:
    guard += 1
    tag = p[i]
    if tag == 0x08:
        v = int.from_bytes(p[i + 1:i + 5], 'little')
        print('  [%3d] 08 u32 = %d' % (i, v))
        i += 5
    elif tag == 0x10:
        e = p.find(b'\x00', i + 1)
        if e < 0:
            print('  [%3d] 10 string (无终止)' % i)
            break
        s = p[i + 1:e]
        print('  [%3d] 10 string = %r' % (i, s))
        i = e + 1
    elif tag == 0x13 and i + 1 < len(p) and p[i + 1] == 0x08:
        ln = int.from_bytes(p[i + 2:i + 6], 'little')
        print('  [%3d] 13 08 blob len=%d' % (i, ln))
        i += 6
        if ln <= 0 or ln > len(p) - i:
            print('         (len 越界, 停止)')
            break
        i += ln
    elif tag == 0x0A:
        if i + 9 <= len(p):
            v = int.from_bytes(p[i + 1:i + 9], 'little')
            print('  [%3d] 0a u64 = 0x%016X' % (i, v))
            i += 9
        else:
            i += 1
    else:
        print('  [%3d] 未知 tag 0x%02X' % (i, tag))
        i += 1

cov.close()
f.close()
