import json
p=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_randrun3\local_listeners.jsonl'
for l in open(p,encoding='utf-8'):
    o=json.loads(l)
    if o.get('port')==8081 and o.get('data_hex'):
        d=bytes.fromhex(o['data_hex'])
        print('len=%d head=%s tail=%s'%(len(d),d[:16].hex(' '),d[-8:].hex(' ')))
