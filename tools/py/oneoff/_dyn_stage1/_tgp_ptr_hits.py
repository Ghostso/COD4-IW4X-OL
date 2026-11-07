from pathlib import Path
import struct
p=Path(r'WeGame/tgp_daemon.exe');d=p.read_bytes()
for name,va in [('GetEnvW',0x8c6084),('GetCmdW',0x8c6088),('GetCmdA',0x8c608c),('CreateProcessW',0x8c6090),('CreateFileMappingW',0x8c6094),('CreateMutexA',0x8c60a0),('MapViewOfFile',0x8c60a8),('CreateFileW',0x8c6114),('CmdLineToArgvW',0x8c6440)]:
 ptr=struct.pack('<I',va);hits=[];st=0
 while True:
  i=d.find(ptr,st)
  if i<0:break
  hits.append(i);st=i+1
 print(name,hex(va),[(hex(i),d[i-2:i+6].hex()) for i in hits])
