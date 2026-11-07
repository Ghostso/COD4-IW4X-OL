# -*- coding: utf-8 -*-
import os, re, io
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
pats = {
  'findSessions': re.compile(rb'findSessions'),
  'mmbook':       re.compile(rb'mmbook'),
  'mmstart':      re.compile(rb'mmstart'),
  '21/5':         re.compile(rb'21/5'),
  '6/14':         re.compile(rb'6/14'),
  'session 对象':  re.compile('session 对象'.encode('utf-8')),
  '原始 payload':  re.compile('原始 payload'.encode('utf-8')),
}
hits = {}
for fn in sorted(os.listdir(KIT)):
    p = os.path.join(KIT, fn)
    if not os.path.isfile(p): continue
    if os.path.getsize(p) > 40_000_000: continue
    try:
        b = open(p, 'rb').read()
    except Exception:
        continue
    for k, rx in pats.items():
        n = len(rx.findall(b))
        if n:
            hits.setdefault(k, []).append((fn, n))

for k in pats:
    lst = hits.get(k, [])
    lst.sort(key=lambda x: -x[1])
    print("=== %s : %d files ===" % (k, len(lst)))
    for fn, n in lst[:10]:
        print("   %-46s x%d" % (fn, n))
    print()
