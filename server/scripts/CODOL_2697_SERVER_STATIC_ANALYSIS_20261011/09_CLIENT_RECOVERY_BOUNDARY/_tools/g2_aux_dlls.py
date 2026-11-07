
import pefile,hashlib,re,struct
paths={
 'client_room':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll',
 'loopback':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll'
}
out=[]
for name,p in paths.items():
 d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=False)
 out.append('===== %s =====' % name)
 out.append('path=%s size=%d sha=%s imagebase=%#x entry=%#x' % (p,len(d),hashlib.sha256(d).hexdigest(),pe.OPTIONAL_HEADER.ImageBase,pe.OPTIONAL_HEADER.AddressOfEntryPoint))
 try:
  for ent in pe.DIRECTORY_ENTRY_IMPORT:
   out.append('IMPORT '+ent.dll.decode('latin1')+': '+', '.join((i.name.decode('latin1') if i.name else '#'+str(i.ordinal)) for i in ent.imports))
 except Exception as e: out.append('IMPORT ERR '+repr(e))
 try:
  for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
   out.append('EXPORT %s ord=%s rva=%#x' % (e.name.decode('latin1') if e.name else '',e.ordinal,e.address))
 except Exception as e: out.append('EXPORT ERR '+repr(e))
 # strings
 for term in [b'serverCommand',b'gamestate',b'snapshot',b'opcode',b'command',b'reliable',b'connect',b'challenge',b'room',b'0x02']:
  hits=[];st=0
  while True:
   j=d.lower().find(term.lower(),st)
   if j<0:break
   a=max(0,j-40);b=min(len(d),j+120);s=''.join(chr(x) if 32<=x<127 else '.' for x in d[a:b]);hits.append((j,s));st=j+1
  for j,s in hits[:20]:out.append('STR %r file=%#x %r' % (term.decode(),j,s))
 out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_aux_dlls.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1200]))
