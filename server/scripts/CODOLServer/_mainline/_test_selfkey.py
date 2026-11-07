import json
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\SINGLE_V3\local_listeners.jsonl'
pk=[bytes.fromhex(json.loads(l)['data_hex']) for l in open(p,encoding='utf-8') if l.strip() and json.loads(l).get('port')==8081 and json.loads(l).get('data_hex')]
print('packets',len(pk))
def dec(k,b):
    d=Cipher(algorithms.AES(k),modes.ECB()).decryptor(); return d.update(b)+d.finalize()
for i,p in enumerate(pk):
    k=p[:16]; ct=p[16:-4]
    print('\n#%d len=%d key=%s'%(i,len(p),k.hex()))
    if len(ct)%16:
        print(' ct not block aligned',len(ct)); continue
    pt=dec(k,ct)
    print(' pt=',pt.hex(' '))
    print(' asc=',''.join(chr(c) if 32<=c<127 else '.' for c in pt[:128]))
