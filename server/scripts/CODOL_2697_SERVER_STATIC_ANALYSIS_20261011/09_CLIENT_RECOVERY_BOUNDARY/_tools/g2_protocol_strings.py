
import pefile,re,struct
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
sections=[]
for s in pe.sections:
 sections.append((s.Name.rstrip(b'\0').decode('latin1'),s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData))
def rva_of(off):
 for nm,va,ptr,rsz in sections:
  if ptr<=off<ptr+rsz:return va+off-ptr
 return None
terms=['netchan','servercommand','gamestate','snapshot','reliable','configstring','cl_parseservermessage','parse server','invalid server','bad server','svc_','eof','command','packet','message','challenge','connect']
out=[]
for term in terms:
 for enc,label in [(term.encode('latin1'),'ascii'),(term.encode('utf-16le'),'utf16')]:
  st=0
  while True:
   j=d.find(enc,st)
   if j<0:break
   rva=rva_of(j)
   if rva is not None:
    # extract nearby printable ascii
    a=max(0,j-32);b=min(len(d),j+160)
    raw=d[a:b]
    # remove nonprintables
    printable=''.join(chr(x) if 32<=x<127 else '.' for x in raw)
    out.append('%s %-5s off=%#x rva=%#x text=%r' % (term,label,j,rva,printable))
   st=j+1
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_protocol_strings.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1000]))
