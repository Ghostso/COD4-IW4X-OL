"""找 0x6371F0 的所有调用者, 判断房间推送走哪条客户端路径。"""
import os
import struct
import sys

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
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


def callers(target):
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
            if base + i + 5 + rel == target:
                hits.append(base + i)
    return hits


md = Cs(CS_ARCH_X86, CS_MODE_32)
targets = [('0x6371F0 room_chan', 0x006371F0),
           ('0x7F1060 push_recv', 0x007F1060),
           ('0x7E7C90 router', 0x007E7C90)]

for name, va in targets:
    hits = callers(va)
    print('=== %s: %d 个直接 call ===' % (name, len(hits)))
    for h in hits[:6]:
        print('   调用点 0x%08X' % h)
        code = read_at(h - 0x50, 0x60)
        if not code:
            continue
        for ins in md.disasm(code, h - 0x50):
            mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
            print('     %08X  %-18s %s %s%s' % (ins.address, ins.bytes.hex(),
                                                ins.mnemonic, ins.op_str, mark))
            if ins.address > h + 0x10:
                break
    print()
