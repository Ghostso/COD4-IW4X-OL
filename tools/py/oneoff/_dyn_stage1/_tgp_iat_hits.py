from pathlib import Path
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=Path(r'WeGame/tgp_daemon.exe');d=p.read_bytes();pe=pefile.PE(data=d,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
sites=[('GetEnvW',0x8c6084),('GetCmdW',0x8c6088),('GetCmdA',0x8c608c),('CreateProcessW',0x8c6090),('CreateFileMappingW',0x8c6094),('CreateMutexA',0x8c60a0),('MapViewOfFile',0x8c60a8),('CreateFileW',0x8c6114),('CmdLineToArgvW',0x8c6440)]
md=Cs(CS_ARCH_X86,CS_MODE_32)
for name,va in sites:
 ptr=struct.pack('<I',va);pat=b'\xff\x15'+ptr;hits=[];st=0
 while True:
  i=d.find(pat,st)
  if i<0:break
  hits.append(i);st=i+1
 print('\n'+name,hex(va),'calls',[(hex(o),hex(pe.get_rva_from_offset(o))) for o in hits])
 for off in hits:
  s=max(0,off-64);r0=pe.get_rva_from_offset(s)
  print(' CALL',hex(pe.get_rva_from_offset(off)))
  for ins in md.disasm(d[s:off+16],base+r0):
   if base+pe.get_rva_from_offset(off)<=ins.address<base+pe.get_rva_from_offset(off)+8: print('   ',hex(ins.address-base),ins.bytes.hex(),ins.mnemonic,ins.op_str)
