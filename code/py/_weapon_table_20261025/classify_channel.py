# -*- coding: utf-8 -*-
"""Classify every trio item by acquisition channel using ID patterns, then
emit the final full list."""
import csv, os, io, sys, collections, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
SRC = os.path.join(BASE, 'codol_callsign_full_census.csv')
OUT = os.path.join(BASE, 'codol_callsign_full_catalog.csv')

# ordered rules: first match wins.  (regex on lowered ID, channel label)
RULES = [
    (r'^pc[bcinf]?_?(default)$',            '默认'),
    (r's\d+(bronze|silver|gold|platinum|diamond|glory|wargod)', '赛季奖励'),
    (r'wargod',                              '战神/赛季奖励'),
    (r'bounty',                              '赏金活动'),
    (r'zchamp|zarena',                       '僵尸冠军/竞技场'),
    (r'zhunt|zombie',                        '僵尸围城'),
    (r'challenge|_ch_',                      '挑战任务'),
    (r'daily',                               '每日任务'),
    (r'weekly',                              '周任务'),
    (r'clan|\bcl\d',                         '战队系统'),
    (r'wegame|tgp|qq',                       '平台活动'),
    (r'event',                               '活动限定'),
    (r'season|s\d{1,2}_',                    '赛季'),
    (r'reward|prize|champ',                  '比赛/排名奖励'),
    (r'prestige|pres\d',                     '转生奖励'),
    (r'rank|level',                          '等级奖励'),
    (r'collect|expert|master|marksman',      '成就解锁'),
    (r'alpha|cb\d?|tgelite|elite',           '资格/精英'),
    (r'promo|special|limited',               '促销限定'),
]

rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))
chan = collections.Counter()
for r in rows:
    sid = r['ID'].lower()
    label = None
    if r['获取途径'] == '商城购买':
        label = '商城购买'
    else:
        for rx, lab in RULES:
            if re.search(rx, sid):
                label = lab
                break
        if label is None:
            label = '其他/未知'
    r['获取途径'] = label
    chan[label] += 1

print('%-14s %6s' % ('获取途径', '条目'))
for k, v in chan.most_common():
    print('%-14s %6d' % (k, v))
print('%-14s %6d' % ('合计', sum(chan.values())))

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['类别', 'ID', '名称键', '中文名', 'itemId',
                                       '商城SKU数', '获取途径'])
    w.writeheader()
    w.writerows(rows)
print('\nwrote', OUT, len(rows), 'rows')

print('\n=== 各类别 x 途径 ===')
cross = collections.defaultdict(collections.Counter)
for r in rows:
    cross[r['类别']][r['获取途径']] += 1
for lab in ('名片背景', '徽章', '称号', '边框', '名牌'):
    c = cross[lab]
    if not c:
        continue
    print('%-8s %s' % (lab, ', '.join('%s=%d' % (k, v) for k, v in c.most_common(6))))
