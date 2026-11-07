"""找 0x7F1060 (dwLobbyEventHandler 槽6) 的调用者 —— 它经 vtable 槽 [6] 调用。

做法: 全镜像搜 `call dword ptr [reg + 0x18]` / `[reg+0x18]` 形式
     (槽6 = vtable+6*4 = +0x18), 并结合上下文判断是不是 dwLobbyEventHandler。

同时列出该 vtable 各槽的 ret 字节数, 推断参数个数:
    0x7F1060 是 ret 0x20 -> 8 个 dword 参数 (含 this)
"""
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


md = Cs(CS_ARCH_X86, CS_MODE_32)

print('=== 各槽的 ret 立即数(推断参数个数) ===')
VT = 0x00DE07A4
for i in range(12):
    h = read_at(VT + i * 4, 4)
    if not h:
        continue
    v = struct.unpack('<I', h)[0]
    code = read_at(v, 0x30) if 0x400000 <= v < 0x1000000 else None
    if not code:
        print('  [%2d] 0x%08X = 0x%08X (非代码)' % (i, VT + i * 4, v))
        continue
    ins = list(md.disasm(code, v))
    ret = next((x for x in ins if x.mnemonic == 'ret'), None)
    print('  [%2d] 0x%08X = 0x%08X  %s %s'
          % (i, VT + i * 4, v, ret.mnemonic if ret else '?', ret.op_str if ret else ''))

print()
print('=== 搜 call dword ptr [reg+0x18] (vtable 槽6) ===')
hits = []
for base, size, fn, prot in regions:
    if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
        continue
    data = blob(fn)
    if len(data) != size:
        continue
    for i in range(size - 3):
        # ff 5x 18  /  ff 9x 18 00 00 00
        if data[i] == 0xFF and (data[i + 1] & 0xF8) == 0x50 and data[i + 2] == 0x18:
            hits.append(base + i)
        elif data[i] == 0xFF and (data[i + 1] & 0xF8) == 0x90:
            if data[i + 2:i + 6] == b'\x18\x00\x00\x00':
                hits.append(base + i)
print('  命中 %d 处' % len(hits))
for h in hits[:12]:
    print('    0x%08X' % h)
