
import pefile,struct
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
s=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.rimp')
raw=d[s.PointerToRawData:s.PointerToRawData+s.Misc_VirtualSize]
out=[]
for step in (8,12,16):
 out.append('===== step %d ====='%step)
 recs=len(raw)//step
 for i in range(min(20,recs)):
  vals=struct.unpack_from('<%dI'%(step//4),raw,i*step)
  out.append('%03d '%i+ ' '.join('%#010x'%v for v in vals))
# classify dword value ranges
ranges={}
for i in range(0,len(raw)-3,4):
 v=struct.unpack_from('<I',raw,i)[0]
 k='zero' if v==0 else 'rimp' if 0xdc11000<=v<0xdc14000 else 'rdata' if 0x7ae000<=v<0x8f1000 else 'text' if 0x1000<=v<0x7ada0b else 'other'
 ranges[k]=ranges.get(k,0)+1
out.append('RANGES '+repr(ranges))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_rimp_records.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
