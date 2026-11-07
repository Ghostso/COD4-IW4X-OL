import json, hashlib, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
g = json.load(open(os.path.join(R,'_golden_hashes.json'), encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest().upper()
bad=[]
for n,e in g.items():
    if not isinstance(e,dict) or 'sha256' not in e: continue
    f=os.path.join(R,n)
    if not os.path.isfile(f): bad.append(n+': missing'); continue
    sz=os.path.getsize(f); h=sha(f)
    if sz!=int(e['size']): bad.append('%s: size %d != %s'%(n,sz,e['size']))
    elif h!=e['sha256'].upper(): bad.append(n+': sha mismatch')
print('受保护条目数 =', sum(1 for e in g.values() if isinstance(e,dict) and 'sha256' in e))
if not bad: print('  ★ 全部匹配，受保护原件未被改动')
else:
    for b in bad: print('  !!', b)
print()
print('lobby_server.py 期望:', g.get('lobby_server.py',{}).get('size'), g.get('lobby_server.py',{}).get('sha256','')[:16])
print('REF_LOBBY_KIT 实际:', os.path.getsize(os.path.join(R,'lobby_server.py')))
