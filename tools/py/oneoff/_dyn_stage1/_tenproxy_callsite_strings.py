from pathlib import Path
import hashlib, struct, pefile
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
mods=[ROOT/r"COD OL\codoMP_client_shipRetail.exe",ROOT/r"COD OL\codoMP_client_shipRetailBase.dll",ROOT/r"COD OL\TenProxy.dll",ROOT/r"COD OL\TCLS\Client.exe",ROOT/r"COD OL\TCLS\ClientBase.dll"]
needles=['TenProxy','Invoke','TclsProxy','CTclsProxy']
for p in mods:
 d=p.read_bytes(); print('\n===',p.name,'===')
 for n in needles:
  for enc in ('ascii','utf-16le'):
   nb=n.encode(enc); hits=[]; st=0
   while True:
    i=d.find(nb,st)
    if i<0: break
    hits.append(i); st=i+1
   if hits: print(n,enc,[hex(x) for x in hits[:40]],'count',len(hits))
 try: pe=pefile.PE(data=d,fast_load=False)
 except Exception as e: print('pe fail',e); continue
 found=[]
 for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
  dll=(ent.dll.decode(errors='replace') if isinstance(ent.dll,bytes) else str(ent.dll))
  if 'TenProxy' in dll or 'tenproxy' in dll.lower():
   for x in ent.imports or []:
    found.append((dll,x.name.decode(errors='replace') if x.name else 'ORD'+str(x.ordinal),hex(x.address)))
 print('imports',found)
