
import pefile,re,hashlib
paths={'main':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin','room':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll','loop':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll'}
out=[]
for name,p in paths.items():
 d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=False)
 out.append('===== %s =====' % name)
 try:
  for ent in pe.DIRECTORY_ENTRY_IMPORT:
   dll=ent.dll.decode('latin1')
   if any(k in dll.lower() for k in ('ten','iips','ifs','proxy','steam','tp','qb','nprotect')) or name!='main':
    out.append('IMPORT '+dll+': '+', '.join((i.name.decode('latin1') if i.name else '#'+str(i.ordinal)) for i in ent.imports))
 except Exception as e:out.append('IMPORT ERR '+repr(e))
 for term in [b'TenProxy',b'IIPS',b'IFS',b'tenproxy',b'iips',b'ifs',b'TenIO',b'Tencent',b'tenio',b'tss',b'TssSdk',b'Steam']:
  st=0;hits=[]
  while True:
   j=d.find(term,st)
   if j<0:break
   hits.append(j);st=j+1
  if hits:
   out.append('STR %r count=%d first=%s' % (term.decode(),len(hits),[hex(x) for x in hits[:10]]))
 out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_platform_boundary.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1000]))
