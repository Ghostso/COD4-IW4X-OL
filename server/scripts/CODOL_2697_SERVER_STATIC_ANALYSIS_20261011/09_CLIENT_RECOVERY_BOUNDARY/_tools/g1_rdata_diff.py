
import pefile
op=r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe'
rp=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
od=open(op,'rb').read();rd=open(rp,'rb').read();ope=pefile.PE(data=od,fast_load=True);rpe=pefile.PE(data=rd,fast_load=True)
def sec(pe,va):
 for s in pe.sections:
  if s.VirtualAddress==va:return s
 return None
so=sec(ope,0x7ae000);sr=sec(rpe,0x7ae000)
a=od[so.PointerToRawData:so.PointerToRawData+so.SizeOfRawData];b=rd[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
runs=[];st=None
for i in range(min(len(a),len(b))):
 if a[i]!=b[i] and st is None:st=i
 if (a[i]==b[i] or i==min(len(a),len(b))-1) and st is not None:
  en=i if a[i]==b[i] else i+1
  runs.append((st,en));st=None
print('diff bytes',sum(e-s for s,e in runs),'runs',len(runs))
for s,e in sorted(runs,key=lambda x:x[1]-x[0],reverse=True)[:30]:
 print('rva=%#x len=%d orig=%s rec=%s'%(0x7ae000+s,e-s,a[s:e].hex(),b[s:e].hex()))
