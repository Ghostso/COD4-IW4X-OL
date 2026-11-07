"""在快照里定位 Scaleform 的电影/菜单对象。

Scaleform GFx 的典型结构:
    - GFxMovieDef / GFxMovieRoot 对象，vtable 已知
    - AS 变量存在 GFxValue 数组里
    - 字符串 "SetReadyState" 等若被 Flash 调过，会有引用

思路 A: 找 "SetReadyState" 等字符串在快照里**是否被引用**
        （MEMDUMP 里零引用，但那是 t 较早的快照；
         建房后的快照可能有）

思路 B: 找 scaleform_ash 开头的资源名，反查其对象

先做 A: 在 snap_003 / snap_004 里搜字符串地址的 dword 引用。
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
NAMES = {
    0x00DDD504: 'SetReadyState',
    0x00DDD514: 'GetReadyState',
    0x00DDD538: 'IsRoomHost',
    0x00DDD5E0: 'GetRoomInfo',
    0x00DDD5A4: 'ChangeTeam',
}

for snap in ('snap_003', 'snap_004'):
    bin_p = os.path.join(RUN, snap + '.bin')
    cov_p = os.path.join(RUN, snap + '_cover.bin')
    if not (os.path.isfile(bin_p) and os.path.isfile(cov_p)):
        continue
    meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
    lo = meta['lo']
    size = os.path.getsize(bin_p)
    print('=== %s t=%.1fs  %.1f MB ===' % (snap, meta['t'], size / 1048576))
    cov = open(cov_p, 'r+b')
    f = open(bin_p, 'rb')

    def covered(va, n):
        off = va - lo
        if off < 0:
            return False
        cov.seek(off)
        return cov.read(n) == b'\x01' * n

    # 先确认字符串本身在不在
    for saddr, name in NAMES.items():
        d = None
        if covered(saddr, 24):
            f.seek(saddr - lo)
            d = f.read(24)
        ok = d is not None and d.startswith(name.encode())
        print('  串 %-16s @0x%08X 存在=%s' % (name, saddr, ok))

    print('  --- 搜 dword 引用 ---')
    for saddr, name in NAMES.items():
        needle = struct.pack('<I', saddr)
        hits = []
        pos = 0
        while pos < size and len(hits) < 20:
            cov.seek(pos)
            if cov.read(1) != b'\x01':
                pos += 1 << 20
                continue
            f.seek(pos)
            data = f.read(min(8 << 20, size - pos))
            if not data:
                break
            i = data.find(needle)
            while i >= 0 and len(hits) < 20:
                a = lo + pos + i
                if a % 4 == 0:
                    hits.append(a)
                i = data.find(needle, i + 1)
            pos += max(1, len(data) - 4)
        print('    %-16s %d 处 %s' % (name, len(hits), [hex(h) for h in hits[:5]]))
    cov.close()
    f.close()
    print()
