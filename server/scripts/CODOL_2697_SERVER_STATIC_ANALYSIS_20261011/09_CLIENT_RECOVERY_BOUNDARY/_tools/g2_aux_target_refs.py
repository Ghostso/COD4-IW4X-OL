
import pefile,struct,hashlib
paths=[r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll',r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll']
targets=[0xA2E50,0xA2D90,0x1AC1D0,0x1ACB00,0x8612E,0x860DE]
out=[]
for p in paths:
 d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
 out.append('===== %s IB=%#x SHA=%s =====' % (p,ib,hashlib.sha256(d).hexdigest()))
 for r in targets:
  for label,val in [('RVA',r),('VA400',0x400000+r),('VA100',0x10000000+r)]:
   b=struct.pack('<I',val);st=0;hits=[]
   while True:
    j=d.find(b,st)
    if j<0:break
    hits.append(hex(j));st=j+1
   if hits:out.append('TARGET %#x %s=%#x refs=%s' % (r,label,val,','.join(hits)))
 out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_aux_target_refs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
