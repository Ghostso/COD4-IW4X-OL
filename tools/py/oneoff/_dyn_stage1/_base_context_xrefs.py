from pathlib import Path
import pefile, struct
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
out=root/r'_dyn_stage1\base_context_xrefs.txt'
files=[r'COD OL\codoMP_client_shipRetailBase.dll',r'COD OL\codoMP_client_shipRetail.exe']
terms=[b'TCLS_SHAREDMEMEMORY',b'TCLS_TASMEMORY_',b'tcls_core',b'TP3GameGuardShareMapping',b'TCLSHOST_MUTEX',b'tcls_core.exe',b'TPUSERACCOUNT_SHAREDMEMEMORY',b'XTDL2',b'WIN_NO_TCLS',b'IsTCLSLogOn']
with out.open('w',encoding='utf-8') as f:
 for rel in files:
  p=root/rel; pe=pefile.PE(str(p),fast_load=True); data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
  f.write(f'FILE {p} base={base:08X}\n')
  for raw in terms:
   hits=[]; pos=0
   while True:
    i=data.find(raw,pos)
    if i<0: break
    try: rva=pe.get_rva_from_offset(i)
    except Exception: pos=i+1; continue
    hits.append((i,rva,base+rva)); pos=i+1
   if not hits: continue
   f.write(f'\nTERM {raw.decode()}\n')
   for off,rva,va in hits:
    f.write(f' STR off={off:08X} rva={rva:08X} va={va:08X}\n')
    pat=struct.pack('<I',va); q=0
    while True:
     j=data.find(pat,q)
     if j<0: break
     try: rr=pe.get_rva_from_offset(j)
     except Exception: q=j+1; continue
     f.write(f'  PTR off={j:08X} rva={rr:08X} va={base+rr:08X}\n'); q=j+1
print(out)
