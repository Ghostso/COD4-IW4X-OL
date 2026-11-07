"""找谁引用运行时构造的 AS_* 类名（0xE76Cxx 一带）。

这些名字是 Scaleform 绑定的关键。若代码里有引用，
就能顺着找到注册函数，进而看到每个 API 的实现。
"""
import json
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
TARGETS = {
    0x00E76C98: 'AS_SetReadyState',
    0x00E76C78: 'AS_GetReadyState',
    0x00E76C5C: 'AS_IsRoomHost',
    0x00E76AFC: 'AS_GetRoomInfo',
    0x00E76CE0: 'AS_StartMatch',
    0x00E76A20: 'AS_VoteMap',
}

snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
size = os.path.getsize(os.path.join(RUN, snap + '.bin'))
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


def scan(needle, limit=30):
    hits = []
    pos = 0
    CH = 16 << 20
    while pos < size and len(hits) < limit:
        cov.seek(pos)
        if cov.read(1) != b'\x01':
            pos += CH
            continue
        f.seek(pos)
        data = f.read(min(CH, size - pos))
        if not data:
            break
        i = data.find(needle)
        while i >= 0 and len(hits) < limit:
            a = lo + pos + i
            if a % 4 == 0:
                hits.append(a)
            i = data.find(needle, i + 1)
        pos += max(1, len(data) - len(needle))
    return hits


md = Cs(CS_ARCH_X86, CS_MODE_32)
for saddr, name in TARGETS.items():
    hits = scan(struct.pack('<I', saddr))
    print('=== %-16s @0x%08X 被引用 %d 处: %s'
          % (name, saddr, len(hits), [hex(h) for h in hits[:6]]))
    for h in hits[:2]:
        code = read(h - 0x30, 0x70)
        if not code:
            continue
        print('  --- 0x%08X ---' % h)
        for n, ins in enumerate(md.disasm(code, h - 0x30)):
            mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
            print('    %08X  %-18s %s %s%s'
                  % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
            if n > 14:
                break
    print()

cov.close()
f.close()
