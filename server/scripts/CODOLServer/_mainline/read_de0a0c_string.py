"""读出 0xDE0A0C 处的固定串(slot6 里 strcmp 的右操作数), 以及周边串。

0x7F3440:
    mov ecx, 0xde0a0c
    cmp 逐字节比较 [esi] 与 [ecx]
    esi = [ebp+0x18]  (slot6 的第 4 个参数)
相等才把 esi 指向的串拷贝到 edi 指向的栈缓冲。
"""
import os
import struct

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


def cstr(va, maxn=96):
    b = read_at(va, maxn)
    if not b:
        return None
    e = b.find(b'\x00')
    return b[:e if e >= 0 else maxn]


for va in (0x00DE0A0C, 0x00DE0A00, 0x00DE0A10, 0x00DE09F0, 0x00DE0A30):
    b = cstr(va)
    print('0x%08X: %r' % (va, b))

print()
print('--- 0xDE0A0C 前后 128 字节原始 ---')
raw = read_at(0x00DE09E0, 0x90)
print(raw.hex() if raw else '(不可读)')
print()
print('--- 可打印串 ---')
if raw:
    cur = bytearray()
    base = 0x00DE09E0
    for i, c in enumerate(raw):
        if 32 <= c < 127:
            cur.append(c)
        else:
            if len(cur) >= 4:
                print('  0x%08X: %s' % (base + i - len(cur), cur.decode()))
            cur = bytearray()
    if len(cur) >= 4:
        print('  0x%08X: %s' % (base + len(raw) - len(cur), cur.decode()))
