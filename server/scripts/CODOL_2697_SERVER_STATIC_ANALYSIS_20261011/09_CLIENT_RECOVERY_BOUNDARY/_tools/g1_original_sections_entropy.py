
import pefile,math,hashlib,struct
p=r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True)
out=[]
for i,s in enumerate(pe.sections):
 raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
 freq=[0]*256
 for b in raw:freq[b]+=1
 ent=-sum((c/len(raw))*math.log2(c/len(raw)) for c in freq if c)
 nm=s.Name.rstrip(b'\0').decode('latin1')
 sig=raw[:64]
 out.append('SEC[%d] %s VA=%#x VSZ=%#x RAW=%#x ENT=%.4f MZ=%s PE=%s' % (i,nm,s.VirtualAddress,s.Misc_VirtualSize,len(raw),ent,raw[:2]==b'MZ',raw.find(b'PE\0\0')>=0))
 out.append('  first64='+sig.hex())
 out.append('  printable='+''.join(chr(x) if 32<=x<127 else '.' for x in sig))
# Check final section for repeated block patterns and high-entropy ranges
s=pe.sections[-1];raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
out.append('FINAL section length %#x unique=%d' % (len(raw),len(set(raw))))
# long runs of same byte
best=(0,0,0)
cur=1;pos=0
for j in range(1,len(raw)):
 if raw[j]==raw[j-1]:
  cur+=1
  if cur>best[0]:best=(cur,pos,raw[j])
 else:cur=1;pos=j
out.append('FINAL longest run=%d at=%#x byte=%#x' % best)
# entropy per 0x10000
for k in range(0,min(len(raw),0x40000),0x10000):
 chunk=raw[k:k+0x10000];fr=[0]*256
 for b in chunk:fr[b]+=1
 ent=-sum((c/len(chunk))*math.log2(c/len(chunk)) for c in fr if c)
 out.append('FINAL_CHUNK +%#x ent=%.4f first=%s' % (k,ent,chunk[:16].hex()))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_original_sections_entropy.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
