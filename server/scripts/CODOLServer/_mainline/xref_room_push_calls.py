"""只读分析：在 MEMDUMP_20261027_v4 里找房间推送链各函数的调用点。

目的：房间 UI 全死（换图/准备/投票点不动）。已知：
  - 我们推送的房间消息当前用的是自造信封 build_room_push
  - 客户端收推送的入口 0x7F1060 -> 0x7E7C90(按 (dword,dword) 路由) -> 0x6371F0 -> 0x637000/0x634870
需要知道 0x7F1060 是谁调的、路由用的两个 dword 从哪个信封字段来。
"""
import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))

CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _prot in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


def find_calls(target):
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
            continue
        data = blob(fn)
        if len(data) != size:
            continue
        for i in range(size - 5):
            if data[i] != 0xE8:
                continue
            rel = struct.unpack_from('<i', data, i + 1)[0]
            addr = base + i
            if addr + 5 + rel == target:
                hits.append(addr)
    return hits


def disasm(va, nbytes=160, label=''):
    code = read_at(va, nbytes)
    print()
    print('=== %s @ 0x%08X ===' % (label, va))
    if not code:
        print('  (unreadable)')
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for n, ins in enumerate(md.disasm(code, va)):
        print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if n >= 60:
            break


TARGETS = {
    'push_receiver_7F1060': 0x007F1060,
    'dispatch_7E7C90': 0x007E7C90,
    'chan_dispatch_6371F0': 0x006371F0,
    'Manifold_ser_625520': 0x00625520,
    'Manifold_de_6256C0': 0x006256C0,
}

for name, va in TARGETS.items():
    hits = find_calls(va)
    print('%s 0x%08X : %d call sites  %s'
          % (name, va, len(hits), [hex(h) for h in hits[:12]]))
    for h in hits[:3]:
        disasm(h - 0x30, 140, name + ' caller before 0x%08X' % h)

print()
print('### Manifold bodies ###')
disasm(0x00625520, 260, 'Manifold.serialize')
disasm(0x006256C0, 300, 'Manifold.deserialize')
