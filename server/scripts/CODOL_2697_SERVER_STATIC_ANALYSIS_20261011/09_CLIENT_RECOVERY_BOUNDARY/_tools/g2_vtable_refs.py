
import pefile,struct
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
secs=[(s.Name.rstrip(b'\0').decode('latin1'),s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def rva_of(off):
 for nm,va,ptr,rsz in secs:
  if ptr<=off<ptr+rsz:return nm,va+off-ptr
 return None,None
targets=[0x775870,0x7758b0,0x775900,0x775940,0x775a00,0x775a50,0x775a80,0x775ab0,0x775af0,0x775b30,0x775b70,0x775bb0]
out=[]
for r in targets:
 for label,val in [('VA',ib+r),('RVA',r)]:
  b=struct.pack('<I',val);st=0
  while True:
   j=d.find(b,st)
   if j<0:break
   nm,rr=rva_of(j);out.append('%#x %s=%#x ref_sec=%s ref_rva=%#x file=%#x' % (r,label,val,nm,rr,j));st=j+1
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_vtable_refs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out) or 'none')
