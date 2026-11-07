"""找 dwLobbyEventHandler 槽6 的调用者: 搜 `call [reg+0x18]` 且上下文出现该 vtable。

更精准的做法: 搜"把 vtable 地址 0xDE07A4 加载进寄存器"的位置, 那就是
dwLobbyEventHandler 实例的使用点; 在这些函数里找 call [reg+0x18]。

vtable 也可能来自对象头部(浅拷贝), 故同时搜 0xDE07A4 的 dword 引用。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
VT = 0x00DE07A4
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


pat = struct.pack('<I', VT)
hits = []
for base, size, fn, prot in regions:
    data = blob(fn)
    if len(data) != size:
        continue
    i = data.find(pat)
    while i >= 0:
        hits.append((base + i, prot))
        i = data.find(pat, i + 1)

print('vtable 0x%08X 被引用 %d 次' % (VT, len(hits)))
for va, prot in hits[:20]:
    kind = '代码段' if (prot & 0x10) else '数据段'
    print('  0x%08X  prot=0x%X  %s' % (va, prot, kind))

print()
md = Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 代码段引用点上下文 ===')
for va, prot in hits[:10]:
    if not (prot & 0x10):
        continue
    code = read_at(va - 0x40, 0xA0)
    if not code:
        continue
    print('  --- 0x%08X ---' % va)
    for ins in md.disasm(code, va - 0x40):
        mark = '  <<<' if ins.address <= va < ins.address + ins.size else ''
        print('    %08X  %-20s %s %s%s' % (ins.address, ins.bytes.hex(),
                                           ins.mnemonic, ins.op_str, mark))
        if ins.address > va + 0x30:
            break
