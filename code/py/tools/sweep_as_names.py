"""全树扫描：AS_SetReadyState 等名字出现在哪些文件里。

不只 EXE —— 房间 UI 的后端可能在某个 DLL，
或者根本不在本地文件里（由服务端下发）。
"""
import os

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
NEEDLES = [b'AS_SetReadyState', b'AS_GetReadyState', b'AS_IsRoomHost',
           b'AS_StartMatch', b'AS_VoteMap']

hits = {}
scanned = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(('.dll', '.exe', '.ff', '.ifs', '.dll.local')):
            continue
        p = os.path.join(dirpath, fn)
        try:
            if os.path.getsize(p) > 400 * 1024 * 1024:
                continue
            d = open(p, 'rb').read()
        except Exception:
            continue
        scanned += 1
        for n in NEEDLES:
            if n in d:
                hits.setdefault(p, []).append(n.decode())

print('扫描 %d 个文件' % scanned)
print()
if not hits:
    print('★ 除 EXE 外再无任何文件包含这些名字')
else:
    for p, ns in sorted(hits.items()):
        print('  %-70s %s' % (p.replace(ROOT, 'COD OL'), ns))
