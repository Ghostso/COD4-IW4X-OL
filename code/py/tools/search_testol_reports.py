"""在 505 份 TESTOL 报告里做关键词检索，找出房间/准备/按钮相关的既有成果。"""
import os
import re
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\reports'
KEY = re.compile(r'(?i)(SetReadyState|GetReadyState|dwRoomMatch|MyEventHandler|'
                 r'UiCppRoom|IsRoomHost|memberCount|room\.startgame|'
                 r'11/13|11/4|房间|准备|button|按钮)')

rows = []
for fn in sorted(os.listdir(D)):
    if not fn.endswith('.md'):
        continue
    p = os.path.join(D, fn)
    try:
        t = open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    hits = KEY.findall(t)
    if not hits:
        continue
    # 统计各关键词
    cnt = {}
    for m in KEY.finditer(t):
        k = m.group(0).lower()
        cnt[k] = cnt.get(k, 0) + 1
    rows.append((fn, len(hits), cnt))

print('命中报告 %d / 505' % len(rows))
print()
for fn, total, cnt in sorted(rows, key=lambda x: -x[1]):
    top = sorted(cnt.items(), key=lambda x: -x[1])[:6]
    print('%-58s %4d  %s' % (fn, total, ', '.join('%s×%d' % (k, v) for k, v in top)))
