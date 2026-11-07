import json,os
R=r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
g=json.load(open(os.path.join(R,'_golden_hashes.json'),encoding='utf-8'))
for n,e in g.items():
    if isinstance(e,dict) and 'sha256' in e:
        print('  %-32s size=%s' % (n, e.get('size')))
