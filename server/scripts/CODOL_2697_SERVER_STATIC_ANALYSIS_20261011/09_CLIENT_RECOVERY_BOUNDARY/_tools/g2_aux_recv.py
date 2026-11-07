
import pefile,struct,hashlib
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
paths={'room':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll','loop':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll'}
md=Cs(CS_ARCH_X86,CS_MODE_32);out=[]
for name,p in paths.items():
 d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=False);ib=pe.OPTIONAL_HEADER.ImageBase
 secs=[(s.Name.rstrip(b'\0').decode('latin1'),s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
 def off(r):
  for nm,va,ptr,rsz in secs:
   if va<=r<va+rsz:return ptr+r-va
  return None
 def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
 # collect network IAT
 iats={}
 for ent in pe.DIRECTORY_ENTRY_IMPORT:
  for imp in ent.imports:
   nm=imp.name.decode('latin1') if imp.name else ''
   if nm in ('recv','send','recvfrom','sendto','select','connect','bind','socket','ioctlsocket','WSAGetLastError'):
    iats[nm]=imp.address
 out.append('===== %s %s =====' % (name,p))
 out.append('IAT '+repr({k:hex(v) for k,v in iats.items()}))
 for nm,iat in iats.items():
  b=struct.pack('<I',iat);st=0
  while True:
   j=d.find(b,st)
   if j<0:break
   # determine containing section/rva
   r=None
   for sn,va,ptr,rsz in secs:
    if ptr<=j<ptr+rsz:r=va+j-ptr;sec=sn;break
   if r is not None:
    # ensure instruction boundary by disassembling 8 bytes before
    ok=False; insat=None
    for x in md.disasm(d[off(r)-8:off(r)+12],ib+r-8):
     if x.address-ib<=r<x.address-ib+x.size:
      ok=x.mnemonic in ('call','jmp') and nm in x.op_str;insat=(x.address-ib,x.mnemonic,x.op_str,x.bytes.hex());break
    if ok:out.append('NETCALL %s rva=%#x ins=%r' % (nm,r,insat))
   st=j+1
 # export disasm
 out.append('EXPORTS')
 for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
  out.append('  %s rva=%#x' % (e.name.decode('latin1') if e.name else '',e.address))
  for x in dis(e.address,0x220):out.append('   %08x %-18s %s'%(x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
  out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_aux_recv.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1500]))
