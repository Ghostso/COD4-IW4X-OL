import re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
for q in [b'cef_',b'Scaleform',b'GFx',b'Chrome',b'chromium',b'V8',b'Blink',b'libcef',b'TP3',b'tp3',b'TenProtect',b'VmpVersion',b'VMProtect']:
    print('%-14s %d'%(q.decode(),d.count(q)))
