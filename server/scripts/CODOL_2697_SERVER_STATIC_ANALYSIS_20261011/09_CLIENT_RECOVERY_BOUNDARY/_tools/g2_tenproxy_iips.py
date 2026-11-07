
import pefile,hashlib,os
paths=["D:/BaiduNetdiskDownload/CODOL.NET/Game/CODOL_2.6.9.7/TenProxy.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\atl80.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\bugreport.exe","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\Download.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IFS2.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\iips.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSCheck.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSHost.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSHostApp.exe","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSLaunchRestore.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSRepair.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSStats.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\IIPSVFS.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\iips_policymsg.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\LZMA.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\msvcp80.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\msvcr80.dll","D:\\BaiduNetdiskDownload\\CODOL.NET\\Game\\CODOL_2.6.9.7\\IIPS\\p2papp.dll"]
out=[]
for p in paths:
 try:
  d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=False)
 except Exception as e:
  out.append('ERR %s %r'%(p,e));continue
 out.append('===== %s ====='%p);out.append('size=%d sha=%s imagebase=%#x'%(len(d),hashlib.sha256(d).hexdigest(),pe.OPTIONAL_HEADER.ImageBase))
 try:
  for ent in pe.DIRECTORY_ENTRY_IMPORT:
   names=[i.name.decode('latin1') if i.name else '#'+str(i.ordinal) for i in ent.imports]
   net=[n for n in names if any(k in n.lower() for k in ('recv','send','socket','connect','select','wsa','callback','message'))]
   if net:out.append('IMPORT '+ent.dll.decode('latin1')+': '+', '.join(net))
 except Exception as e:out.append('IMPORT ERR '+repr(e))
 try:
  out.append('EXPORTS '+', '.join((e.name.decode('latin1') if e.name else '#'+str(e.ordinal))+'@'+hex(e.address) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols[:120]))
 except Exception as e:out.append('EXPORT ERR '+repr(e))
 for term in (b'recv',b'message',b'callback',b'packet',b'opcode',b'command',b'snapshot',b'gamestate',b'connect',b'IIPS'):
  hits=[];st=0
  while True:
   j=d.lower().find(term.lower(),st)
   if j<0:break
   a=max(0,j-40);b=min(len(d),j+120);hits.append((j,''.join(chr(x) if 32<=x<127 else '.' for x in d[a:b])));st=j+1
  for j,s in hits[:15]:out.append('STR %r file=%#x %r'%(term.decode(),j,s))
 out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_tenproxy_iips.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1200]))
