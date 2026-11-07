"""弄清 0x7E79C0 的 obj 到底是什么: 它读 [obj+8]/[obj+0xc] 作为 roomId 校验。

可能:
  A. obj 是"消息对象", +8/+0xc 是消息里的 roomId 字段
  B. obj 是房间对象的某个视图, +8 对应房间对象 +0

线索: 房间对象 +0 处是 roomId_lo。若 obj+8 == 房间对象+0，
则 obj = 房间对象 - 8，即 obj 前 8 字节是别的东西(vtable+标志)。

本脚本: 对已知的房间对象地址 0x08425C10 / 0x08426368，
反查"谁在它前面 8 字节处写了什么"，看是否像对象头。
同时搜内存里有没有 dword 等于 (0x08425C10 - 8) 的指针。
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
size = os.path.getsize(os.path.join(RUN, snap + '.bin'))


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


print('=== 房间对象前置 32 字节 ===')
for va in (0x08425C10, 0x08426368):
    d = read(va - 0x20, 0x40)
    if not d:
        print('  0x%08X 不可读' % va)
        continue
    print('0x%08X 前面:' % va)
    for i in range(0, 0x20, 16):
        w = struct.unpack_from('<4I', d, i)
        print('    %+04X  %s' % (i - 0x20, ' '.join('%08X' % x for x in w)))
    print('  --- 对象本体 ---')
    for i in range(0x20, 0x40, 16):
        w = struct.unpack_from('<4I', d, i)
        print('    %+04X  %s' % (i - 0x20, ' '.join('%08X' % x for x in w)))
    print()

print('=== 搜指向"房间对象-8"的指针 ===')
for target in (0x08425C10 - 8, 0x08426368 - 8, 0x08425C10, 0x08426368):
    needle = struct.pack('<I', target)
    hits = []
    pos = 0
    while pos < size:
        cov.seek(pos)
        if cov.read(1) != b'\x01':
            pos += 1 << 20
            continue
        f.seek(pos)
        data = f.read(min(8 << 20, size - pos))
        if not data:
            break
        i = data.find(needle)
        while i >= 0:
            a = lo + pos + i
            if a % 4 == 0:
                hits.append(a)
            i = data.find(needle, i + 1)
        pos += max(1, len(data) - 4)
    print('  0x%08X 被引用 %d 次: %s' % (target, len(hits), [hex(h) for h in hits[:8]]))

cov.close()
f.close()
