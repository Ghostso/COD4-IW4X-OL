
import pefile,struct,hashlib,os
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read(); pe=pefile.PE(data=d,fast_load=False)
out=[]; net=[]
for ent in pe.DIRECTORY_ENTRY_IMPORT:
 dll=ent.dll.decode('latin1').lower()
 for imp in ent.imports:
  name=imp.name.decode('latin1') if imp.name else ''
  if any(k in name.lower() for k in ('recv','send','select','socket','connect','accept','closesocket','getaddrinfo','wsagetlasterror','htons','htonl')):
   net.append((dll,name,imp.address))
   out.append('%s %s iat=%#x' % (dll,name,imp.address))
# byte refs to IAT slots in .text and .tvm0
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text'); tv=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.tvm0')
out.append('\nIAT XREFS IN .text')
for dll,name,iat in net:
 b=struct.pack('<I',iat); st=text.PointerToRawData; end=st+text.SizeOfRawData
 while True:
  j=d.find(b,st,end)
  if j<0: break
  out.append('%s %s iat=%#x ref_rva=%#x ref_off=%#x' % (dll,name,iat,text.VirtualAddress+j-text.PointerToRawData,j)); st=j+1
out.append('\nIAT XREFS IN .tvm0')
for dll,name,iat in net:
 b=struct.pack('<I',iat); st=tv.PointerToRawData; end=st+tv.SizeOfRawData
 while True:
  j=d.find(b,st,end)
  if j<0: break
  out.append('%s %s iat=%#x ref_rva=%#x ref_off=%#x' % (dll,name,iat,tv.VirtualAddress+j-tv.PointerToRawData,j)); st=j+1
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_iat_xrefs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
