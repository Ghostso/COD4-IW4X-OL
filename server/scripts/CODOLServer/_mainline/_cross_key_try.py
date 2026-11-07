import json,os,glob,struct
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
def dec(k,b):
    d=Cipher(algorithms.AES(k),modes.ECB()).decryptor(); return d.update(b)+d.finalize()
# collect ALL runs that have 8081 packets, and try every 16-byte windows of the
# 8000 request/response as key
for d in sorted(glob.glob(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\*\local_listeners.jsonl'))+sorted(glob.glob(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\*\local_listeners.jsonl')):
    try: rows=[json.loads(l) for l in open(d,encoding='utf-8') if l.strip()]
    except: continue
    ct=[bytes.fromhex(r['data_hex']) for r in rows if r.get('port')==8081 and r.get('data_hex')]
    if not ct: continue
    blobs=[]
    for r in rows:
        if r.get('data_hex'): blobs.append(bytes.fromhex(r['data_hex']))
        if r.get('sent_hex'): blobs.append(bytes.fromhex(r['sent_hex']))
    keys=set()
    for b in blobs:
        for i in range(0,max(0,len(b)-15)):
            keys.add(b[i:i+16])
    hit=0
    for k in keys:
        if k==bytes(16): continue
        try: pt=dec(k,ct[0][:-4][:16])
        except: continue
        if pt[:2] in (b'ur',b'us',b'ru',b'su'):
            print('MATCH',d,'key',k.hex(),'pt',pt.hex()); hit+=1
    print('%s ct=%d trial_keys=%d matches=%d'%(os.path.dirname(d).split('\\')[-1],len(ct),len(keys),hit))
