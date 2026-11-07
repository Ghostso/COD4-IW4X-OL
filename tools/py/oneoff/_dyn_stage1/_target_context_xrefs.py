from pathlib import Path
import pefile, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
files={
 r'COD OL\codoMP_client_shipRetail.exe':{
  'WIN_NO_TCLS':0x00DDBF80,'IsTCLSLogOn_1':0x00DDD298,'IsTCLSLogOn_2':0x00E763EB,'TenProxy':0x00DC6EDC},
 r'COD OL\codoMP_client_shipRetailBase.dll':{
  'TCLS_SHAREDMEMEMORY':0x1088FFFC,'tcls_core':0x1088FB44,'TP3GameGuardShareMapping':0x1088FAFC,'TPUSERACCOUNT_SHAREDMEMEMORY':0x108908D0,'game_id':0x10876BA8,'TenProxy':0x1088FA88},
}
md=Cs(CS_ARCH_X86,CS_MODE_32)
for fn,targets in files.items():
 p=Path(fn); b=p.read_bytes(); pe=pefile.PE(fn,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
 def off_to_va(off):
  for s in pe.sections:
   raw=s.PointerToRawData; sz=s.SizeOfRawData
   if raw<=off<raw+sz: return ib+s.VirtualAddress+(off-raw)
  return None
 def va_to_off(va):
  r=va-ib
  for s in pe.sections:
   if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
    return s.PointerToRawData+(r-s.VirtualAddress)
  return None
 print('\n'+'='*100); print(fn,hex(ib),len(b))
 for name,va in targets.items():
  print('\n###',name,hex(va))
  pat=struct.pack('<I',va); hits=[]; pos=0
  while True:
   i=b.find(pat,pos)
   if i<0: break
   hits.append(i); pos=i+1
  print('raw xrefs',len(hits),[hex(x) for x in hits])
  for i in hits:
   xva=off_to_va(i); print('  OFF',hex(i),'XVA',hex(xva) if xva is not None else None)
   if xva is None: continue
   lo=max(0,va_to_off(xva)-64); hi=min(len(b),va_to_off(xva)+64)
   start=xva-(va_to_off(xva)-lo)
   for ins in md.disasm(b[lo:hi],off_to_va(lo)):
    mark='>>' if ins.address==xva else '  '
    print(f'   {mark}{ins.address:08X} {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}')
