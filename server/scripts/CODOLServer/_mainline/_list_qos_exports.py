import pefile
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
pe=pefile.PE(p,fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
names=[]
try:
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        n=e.name.decode() if e.name else ''
        names.append((e.address,n))
except Exception as ex:
    print('err',ex)
print('total exports',len(names))
import re
kw=re.compile(r'qos|Qos|QOS|crypt|Crypt|AES|aes|key|Key|encrypt|decrypt|Encrypt|Decrypt|tqos',re.I)
hit=[(a,n) for a,n in names if kw.search(n)]
print('crypto/qos-named exports:',len(hit))
for a,n in hit[:120]:
    print('  rva=%08X %s'%(a,n))
