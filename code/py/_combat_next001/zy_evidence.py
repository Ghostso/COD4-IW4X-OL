# -*- coding: utf-8 -*-
import os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
KIT = os.path.join(BASE, 'REF_LOBBY_KIT')
cands = []
for root, dirs, files in os.walk(KIT):
    for fn in files:
        p = os.path.join(root, fn)
        try:
            if os.path.getsize(p) > 20_000_000: continue
            b = open(p, 'rb').read()
        except Exception:
            continue
        m = []
        if b'236' in b and b'findSessions' in b: m.append('236+findSessions')
        if b'service=21 task=5' in b: m.append('svc21/task5')
        if b'306' in b and b'findSessions' in b: m.append('306+findSessions')
        if b'13 08 1d 00 00 00 19 00 00 00' in b: m.append('mmbook-blob-hex')
        if b'mmbook 796' in b: m.append('mmbook796')
        if m: cands.append((fn, len(b), m))
print("=== files with 21/5 or mmbook evidence ===")
for fn, sz, m in sorted(cands, key=lambda x: -x[1]):
    print("   %-45s %8d B  %s" % (fn, sz, ",".join(m)))
print()
p = os.path.join(KIT, 'lobby_tasks.bin')
b = open(p, 'rb').read()
print("lobby_tasks.bin size=%d" % len(b))
i = b.find(b'mmbook')
print("first 'mmbook' offset=%d" % i)
if i > 0:
    print("context: " + b[max(0,i-48):i+64].hex(" "))
print()
print("=== NET_CAPTURE runs ===")
for run in sorted(os.listdir(os.path.join(BASE, 'run_codol_001', 'runs'))):
    if 'NET_CAPTURE' in run: print("   " + run)
