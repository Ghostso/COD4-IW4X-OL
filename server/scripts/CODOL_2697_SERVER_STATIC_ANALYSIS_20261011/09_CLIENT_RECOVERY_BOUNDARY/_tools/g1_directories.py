
import pefile,hashlib,struct
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read(); pe=pefile.PE(data=d,fast_load=False)
out=[]
out.append('IMPORTS')
try:
 for e in pe.DIRECTORY_ENTRY_IMPORT:
  out.append('DLL '+e.dll.decode('latin1'))
  for imp in e.imports:
   out.append('  %s %s' % (hex(imp.address) if imp.address else '?', imp.name.decode('latin1') if imp.name else '#'+str(imp.ordinal)))
except Exception as ex: out.append('ERR '+repr(ex))
out.append('EXPORTS')
try:
 for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
  out.append('%s %s %#x' % (e.name.decode('latin1') if e.name else '', str(e.ordinal), e.address))
except Exception as ex: out.append('ERR '+repr(ex))
out.append('RELOCS')
try:
 out.append('blocks %d' % len(pe.DIRECTORY_ENTRY_BASERELOC))
 for b in pe.DIRECTORY_ENTRY_BASERELOC[:20]:
  out.append('block rva=%#x entries=%d' % (b.struct.VirtualAddress,len(b.entries)))
except Exception as ex: out.append('ERR '+repr(ex))
out.append('TLS')
try:
 t=pe.DIRECTORY_ENTRY_TLS.struct
 out.append('callbacks=%#x index=%#x raw=%#x' % (getattr(t,'AddressOfCallBacks',0),getattr(t,'AddressOfIndex',0),getattr(t,'StartAddressOfRawData',0)))
except Exception as ex: out.append('ERR '+repr(ex))
out.append('DEBUG')
try:
 for dbg in pe.DIRECTORY_ENTRY_DEBUG:
  out.append('type=%#x size=%#x addr=%#x ptr=%#x' % (dbg.struct.Type,dbg.struct.SizeOfData,dbg.struct.AddressOfRawData,dbg.struct.PointerToRawData))
except Exception as ex: out.append('ERR '+repr(ex))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_directories.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
