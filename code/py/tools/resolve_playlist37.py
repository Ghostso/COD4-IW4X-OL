"""搞清楚 mmstart 里 `playlist 37` 的来源。

已知:
    10-26 连通轮: findSessions 请求 [1,0,10,..] (4 值) -> mmstart 带 map
    10-28 各轮  : findSessions 请求 [3,0,50,...] (12 值) 先 50 后 10
                  -> mmstart 只有 "playlist 37"

假设: mmstart 的 "playlist 37" 与 findSessions 的 playlist 不是同一套编号。

做法: 在官方 playlist 表里, 找出哪些 playlist 同时满足
      - 可被客户端选作 BOT 房间
      - 且首图是本地可用的 mp_raid
若 playlist 148 (mp_raid/hp) 在客户端眼里是别的位置, 37 可能指向它。
看看 148 在排序列表里的位置。
"""
import zlib
import re

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\kit_roommsg_20261028\publisher_files\mp_playlists_shipRetail_1.0.0.info'
text = zlib.decompress(open(P, 'rb').read()).decode('latin1')

cur = None
pl = {}
order = []          # 文件里出现的顺序
name = {}
lines = text.splitlines()
for i, line in enumerate(lines):
    m = re.match(r'^\s*playlist\s+(\d+)\s*$', line)
    if m:
        cur = int(m.group(1))
        pl.setdefault(cur, [])
        order.append(cur)
        for j in range(i - 1, max(0, i - 4), -1):
            c = lines[j].strip()
            if c.startswith('//'):
                name[cur] = c
                break
        continue
    if cur is not None:
        m2 = re.match(r'^\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*,\s*\d+', line)
        if m2:
            pl[cur].append((m2.group(1), m2.group(2)))

srt = sorted(pl)
print('playlist 总数 %d' % len(pl))
print('文件出现顺序前 20: %s' % order[:20])
print()

print('=== 含 mp_raid 的 playlist ===')
for pid in srt:
    maps = [m for m, g in pl[pid]]
    if 'mp_raid' in maps:
        idx = srt.index(pid)
        print('  playlist %-4d  排序下标 %-3d  %s' % (pid, idx, pl[pid][:4]))

print()
print('=== 含本地可用图的全部 playlist ===')
LOCAL = {'mp_raid', 'mp_firingrange', 'mp_cargoship',
         'coop_train_mp_firingrange', 'coop_training_mp_cargoship'}
for pid in srt:
    hit = [m for m, g in pl[pid] if m in LOCAL]
    if hit:
        idx = srt.index(pid)
        print('  playlist %-4d 下标 %-3d %-42s %s'
              % (pid, idx, name.get(pid, '')[:42], hit))

print()
print('=== 下标 37 与 50 的真实指向（复核）===')
for idx in (37, 50):
    pid = srt[idx]
    print('  下标 %-3d -> playlist %-4d %s' % (idx, pid, pl[pid][:3]))
print()
print('=== 若 37 是文件出现顺序的下标 ===')
if len(order) > 37:
    print('  顺序下标 37 -> playlist %d %s' % (order[37], pl[order[37]][:3]))
if len(order) > 50:
    print('  顺序下标 50 -> playlist %d %s' % (order[50], pl[order[50]][:3]))
