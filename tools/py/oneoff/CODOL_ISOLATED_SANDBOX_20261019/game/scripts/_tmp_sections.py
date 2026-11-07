from pathlib import Path
import struct
with Path('codoMP_client_shipRetail.exe').open('rb') as f:
 f.seek(0x3c); pe=struct.unpack('<I',f.read(4))[0]
 f.seek(pe+6); n=struct.unpack('<H',f.read(2))[0]
 f.seek(pe+20); oh=struct.unpack('<H',f.read(2))[0]
 so=pe+24+oh
 secs=[]
 for i in range(n):
  f.seek(so+40*i);h=f.read(40)
  name=h[:8].split(b'\0')[0].decode('latin1');vs,va,rs,pr=struct.unpack_from('<IIII',h,8);ch=struct.unpack_from('<I',h,36)[0]
  secs.append((name,va,vs,rs,pr,ch))
 for s in secs:print(s)
