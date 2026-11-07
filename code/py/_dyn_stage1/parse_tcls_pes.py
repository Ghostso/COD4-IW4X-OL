from pathlib import Path
try:
 import pefile
except Exception as e:
 print('NO_PEFILE',e); raise
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
files=[root/r'COD OL\TCLS\Client.exe',root/r'COD OL\TCLS\ClientBase.dll',root/r'COD OL\TCLS\TPSvc.exe',root/r'COD OL\TCLS\tpsvcBase.dll',root/r'COD OL\TP3Helper.exe']
out=[]
def dec(v):
 if v is None: return ''
 if isinstance(v,bytes): return v.decode('utf-8','replace')
 return str(v)
for p in files:
 out.append(f'\n===== {p} =====')
 if not p.exists(): out.append('MISSING'); continue
 try:
  pe=pefile.PE(str(p),fast_load=True)
  dirs=[pefile.DIRECTORY_ENTRY[x] for x in ['IMAGE_DIRECTORY_ENTRY_IMPORT','IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT','IMAGE_DIRECTORY_ENTRY_EXPORT','IMAGE_DIRECTORY_ENTRY_DEBUG','IMAGE_DIRECTORY_ENTRY_TLS']]
  pe.parse_data_directories(directories=dirs)
  out.append(f'size={p.stat().st_size} ts=0x{pe.FILE_HEADER.TimeDateStamp:08X} imagebase=0x{pe.OPTIONAL_HEADER.ImageBase:08X} entry=0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:X} sizeimage=0x{pe.OPTIONAL_HEADER.SizeOfImage:X}')
  for attr,lab in [('DIRECTORY_ENTRY_IMPORT','IMPORT'),('DIRECTORY_ENTRY_DELAY_IMPORT','DELAY')]:
   if hasattr(pe,attr):
    for m in getattr(pe,attr):
     names=[dec(getattr(x,'name',None)) or f'ord:{x.ordinal}' for x in m.imports]
     out.append(lab+' '+dec(m.dll)+' count='+str(len(names))+' '+','.join(names))
  if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
   ex=[(s.ordinal,dec(getattr(s,'name',None)),hex(s.address)) for s in pe.DIRECTORY_ENTRY_EXPORT.symbols]
   out.append('EXPORTS count='+str(len(ex))+' '+repr(ex[:120]))
  if hasattr(pe,'DIRECTORY_ENTRY_DEBUG'):
   for d in pe.DIRECTORY_ENTRY_DEBUG:
    try: out.append('DEBUG '+dec(d.entry.PdbFileName))
    except Exception: pass
 except Exception as e: out.append('ERROR '+repr(e))
Path(root/r'_dyn_stage1\tcls_pe_report.txt').write_text('\n'.join(out),encoding='utf-8')
print('WROTE',len('\n'.join(out)))
