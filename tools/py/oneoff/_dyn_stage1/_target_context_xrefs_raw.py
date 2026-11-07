from pathlib import Path
import struct,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
targets={
 'WIN_NO_TCLS':0x00DDBF80,
 'IsTCLSLogOn_1':0x00DDD298,
 'IsTCLSLogOn_2':0x00E763EB,
 'TenProxy':0x00DC6EDC,
}
base=0x400000
for fn in [r'COD OL\codoMP_client_shipRetail.exe',r'COD OL\codoMP_client_shipRetailBase.dll']:
 b=Path(fn).read_bytes(); ib=0x400000 if fn.endswith('.exe') else 0x10000000
 print('\n====',fn,'size',len(b),'base',hex(ib))
 for name,va in targets.items():
  if not (ib<=va<ib+len(b)) and ib==0x400000: continue
  pat=struct.pack('<I',va)
  pos=[]; start=0
  while True:
   i=b.find(pat,start)
   if i<0: break
   pos.append(i); start=i+1
  print(name,hex(va),'raw', [hex(x) for x in pos])
  for i in pos:
   print(' OFF',hex(i),'VA',hex(ib+i),'BEFORE',b[max(0,i-24):i].hex(' '),'AFTER',b[i:i+32].hex(' '))
  # rva immediate
  r=va-ib; pat2=struct.pack('<I',r); pos2=[]; start=0
  while True:
   i=b.find(pat2,start)
   if i<0: break
   pos2.append(i); start=i+1
  print(name,'rva imm',hex(r),[hex(x) for x in pos2[:20]])
