import json, hashlib, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
kit = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
mp = os.path.join(kit, '_run_once_hashes.json')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest().upper()
m = json.load(open(mp, encoding='utf-8'))
f = os.path.join(kit,'lobby_server.py')
old = m.get('lobby_server.py',{}).get('sha256','<none>')
m['lobby_server.py'] = {'size': os.path.getsize(f), 'sha256': sha(f)}
json.dump(m, open(mp,'w',encoding='utf-8'), indent=2)
print('旧 sha=%s size=%s' % (old[:16], m.get('lobby_server.py',{}).get('size')))
print('新 sha=%s size=%d' % (m['lobby_server.py']['sha256'][:16], m['lobby_server.py']['size']))
print('条目数 =', len(m))
