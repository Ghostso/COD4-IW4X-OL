"""在内存转储里找 dwRoom / dwRoomImp 的运行时对象实例。

思路: RTTI 链被剥离, 但运行时对象一定存在。对象的第一个字段是 vtable 指针。
      vtable 指向 .rdata, 且 vtable[-4] (或附近) 含 CompleteObjectLocator 指针。

做法:
  1. 在全部内存里, 找所有"指向 0x00E60000~0x00E70000 (RTTI 串区) 附近"的 u32
     —— 这些是 TypeDescriptor 的引用, 可能就是 COL.
  2. 反过来: 扫描所有可读区域的 u32, 找值落在 0x00D70000~0x00D80000
     (pVFTable 区, 实测 0x00D77818) 的位置 —— 那可能是 TypeDescriptor 头部。

更直接的做法: 找 vtable —— 特征是连续多个 u32 都指向可执行段 (0x400000..0x1000000),
且前面 4 字节是一个指向 .rdata 的指针 (COL)。
"""
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

CACHE = {}


def blob(base):
    if base not in CACHE:
        CACHE[base] = open(os.path.join(D, regions[base][1]), 'rb').read()
    return CACHE[base]


print('区域 %d 个' % len(regions))

# 找出所有可执行区域 (代码段)
exec_ranges = []
for base, (size, fn) in sorted(regions.items()):
    d = blob(base)
    # 拿不到 Protect, 改用启发式: 找 IMAGE 的 .text 区域
    pass

# 从 regions.txt 里读 protect
prot_map = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        prot_map[int(p[0], 16)] = int(p[2], 16)

def in_exec(va):
    for base, (size, fn) in regions.items():
        if base <= va < base + size:
            prot = prot_map.get(base, 0)
            # 0x20=EXECUTE_READ, 0x40=EXECUTE_READWRITE, 0x10=EXECUTE, 0x80=EXECUTE_WRITECOPY
            return bool(prot & 0xF0)
    return False


def u32_at(va):
    for base, (size, fn) in regions.items():
        if base <= va < base + size and va + 4 <= base + size:
            return struct.unpack('<I', blob(base)[va - base:va - base + 4])[0]
    return None


print()
print('=== 扫描 vtable 候选 ===')
print('特征: 连续 >=6 个 u32 都指向可执行段, 且前一槽指向 .rdata')
cands = []
for base, (size, fn) in sorted(regions.items()):
    protect = prot_map.get(base, 0)
    # vtable 通常在只读数据段, 不在代码段
    if protect & 0xF0:
        continue
    d = blob(base)
    n = len(d) // 4
    for i in range(1, n - 8):
        off = i * 4
        va = base + off
        # 前一个 u32 应是 COL 指针 (指向 .rdata 0x00D00000..0x00F00000 之间)
        prev = struct.unpack('<I', d[off - 4:off])[0]
        if not (0x00C00000 <= prev < 0x01000000):
            continue
        # 连续函数指针
        cnt = 0
        for k in range(6):
            if off + k * 4 + 4 > len(d):
                break
            fn = struct.unpack('<I', d[off + k * 4:off + k * 4 + 4])[0]
            if 0x00400000 <= fn < 0x01000000 and in_exec(fn):
                cnt += 1
            else:
                break
        if cnt >= 6:
            cands.append((va, prev, cnt))

print('候选 %d 个' % len(cands))
for va, col, cnt in cands[:40]:
    print('  vtable=0x%08X  COL=0x%08X  虚函数=%d' % (va, col, cnt))
