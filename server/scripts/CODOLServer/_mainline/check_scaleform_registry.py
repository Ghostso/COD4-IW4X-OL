"""确认这些 Scaleform 方法名是否被注册（即按钮是否真的存在实现）。

Scaleform 里 C++ 注册函数通常这样:
   - 表结构: { name_ptr, handler_ptr }
   - 或调用 RegisterFunction(name, handler)

搜法: 在数据段找 [(0x00DDD504) , handler] 这种成对出现的表项。
     即 8 字节窗口里第一个 dword == 字符串地址。
"""
import os
import struct

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
STRINGS = {
    0x00DDD504: 'SetReadyState',
    0x00DDD514: 'GetReadyState',
    0x00DDD538: 'IsRoomHost',
    0x00DDD5E0: 'GetRoomInfo',
    0x00DDD5A4: 'ChangeTeam',
}

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


for saddr, name in STRINGS.items():
    needle = struct.pack('<I', saddr)
    hits = []
    for base, size, fn, prot in regions:
        d = blob(fn)
        if len(d) != size:
            continue
        i = d.find(needle)
        while i >= 0 and len(hits) < 12:
            if (base + i) % 4 == 0:
                hits.append((base + i, prot))
            i = d.find(needle, i + 1)
    print('=== %s (0x%08X) 在内存中出现 %d 次 ===' % (name, saddr, len(hits)))
    for va, prot in hits[:8]:
        kind = '代码' if (prot & 0x20) else '数据'
        # 看后面 4 字节是不是代码指针
        nxt = None
        for base, size, fn, _p in regions:
            if base <= va + 4 < base + size and va + 8 <= base + size:
                d = blob(fn)
                if len(d) == size:
                    off = va + 4 - base
                    nxt = struct.unpack_from('<I', d, off)[0]
                break
        tag = ''
        if nxt and 0x00400000 <= nxt < 0x01000000:
            tag = '  -> handler 可能是 0x%08X' % nxt
        print('   0x%08X (%s)%s' % (va, kind, tag))
    print()
