
import pefile,struct
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
secs=[(s.Name.rstrip(b'\0').decode('latin1'),s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def rva_of(off):
 for nm,va,ptr,rsz in secs:
  if ptr<=off<ptr+rsz:return nm,va+off-ptr
 return None,None
def off_of(r):
 for nm,va,ptr,rsz in secs:
  if va<=r<va+rsz:return ptr+r-va
 return None
out=[]
for label,val in [('VA',ib+0x89856c),('RVA',0x89856c)]:
 b=struct.pack('<I',val);st=0
 while True:
  j=d.find(b,st)
  if j<0:break
  nm,rr=rva_of(j);out.append('%s %#x ref=%s:%#x file=%#x' % (label,val,nm,rr,j));st=j+1
out.append('--- dwords around vtable ---')
for i in range(-32,64,4):
 r=0x89856c+i;b=d[off_of(r):off_of(r)+4]
 if len(b)==4:out.append('%+#x %#x %s' % (i,struct.unpack('<I',b)[0],b.hex()))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_vtable_around.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
