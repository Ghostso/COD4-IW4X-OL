"""读运行时 dwLobbyEventHandler 实例 0xE39B6E8 的内容。

- 前 4 字节应是 vtable 0xDE07A4
- 其余字段照出来, 找哪两个 dword 像 roomId 高低 32
- 同时反汇编构造器 0x7F0960 附近, 看字段初始化
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


OBJ = 0x0E39B6E8
raw = read_at(OBJ, 0x80)
print('=== 实例 0x%08X 前 0x80 字节 ===' % OBJ)
if raw:
    for i in range(0, len(raw), 16):
        chunk = raw[i:i + 16]
        vals = ' '.join('%08X' % struct.unpack_from('<I', chunk, k)[0]
                        for k in range(0, len(chunk) - 3, 4))
        print('  +%03X  %s' % (i, vals))
else:
    print('  (不可读)')

print()
print('=== 构造器 0x7F0940 起 ===')
md = Cs(CS_ARCH_X86, CS_MODE_32)
code = read_at(0x007F0940, 0x80)
if code:
    for ins in md.disasm(code, 0x007F0940):
        print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(),
                                       ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break
