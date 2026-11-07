"""推断 dwRoomMatch::Init 的触发时机。

已知:
    · 它是 static void，无参
    · 内部定义局部类 MyEventHandler（vtable 0xDC78E8, slot[1]=0x63B500）
    · 函数体在加密节，静态看不到

推理依据:
    C++ 里 `static void X::Init()` 这种形态，典型用法是
    在某个"确保初始化"的地方调用一次：
        if (!s_inited) { X::Init(); s_inited = true; }

要找:
    1. 引用 MyEventHandler 相关全局变量的代码
    2. 或引用 0xDC78E8 附近 vtable 数组的代码

换个角度：`dwRoomMatch` 自己的 vtable 在哪？
    若 dwRoomMatch 是单例，会有 [0x82Exxxx] 全局指针。
    记忆里 [0x82E1518] 是 dwRoomMatchUber，[0x82E13FC] 是 dwRoomImp。

先列出 0x82Exxxx 一带的全局指针，看有没有 dwRoomMatch 的单例。
"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8') if False else []:
    pass
import os
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


print('=== 0x82E13F0 .. 0x82E1540 的全局指针 ===')
for va in range(0x082E13F0, 0x082E1540, 4):
    d = read_at(va, 4)
    if not d:
        continue
    v = struct.unpack('<I', d)[0]
    if v:
        # 读该指针处的前 4 字节（vtable）
        h = read_at(v, 4) if 0x10000 <= v < 0x7FFF0000 else None
        vt = struct.unpack('<I', h)[0] if h else 0
        tag = ''
        if vt == 0x00DC795C:
            tag = '  <- dwRoomMatchUber'
        elif vt == 0x00DC7274:
            tag = '  <- dwRoomImp'
        elif vt == 0x00DC7E6C:
            tag = '  <- dwRoomMatch  ★'
        elif 0x00DC0000 <= vt < 0x00DE0000:
            tag = '  <- vtable 0x%08X' % vt
        print('  [0x%08X] = 0x%08X%s' % (va, v, tag))
