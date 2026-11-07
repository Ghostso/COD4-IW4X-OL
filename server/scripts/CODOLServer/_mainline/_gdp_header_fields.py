import re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr'
d=open(p,'rb').read()
s=[m.group().decode('ascii','replace') for m in re.finditer(rb'[\x20-\x7e]{3,}',d)]
kw=re.compile(r'(PKG|HEAD|MAGIC|VERSION|CMD|BODY|ERROR|RET|LEN|PACK|PROTOCOL)',re.I)
hits=[]
for x in s:
    if kw.search(x): hits.append(x)
print('matches',len(hits))
for x in hits[:200]: print(' ',x)
