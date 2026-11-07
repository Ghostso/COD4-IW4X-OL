"""Read-only C1 map-script renderer dvar identity/value probe; no calls or writes."""
import ctypes,struct,json,argparse
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);a=p.parse_args()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.restype=ctypes.c_void_p;k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.CloseHandle.argtypes=[ctypes.c_void_p]
h=k.OpenProcess(0x10,False,a.pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
def read(x,n):
 b=ctypes.create_string_buffer(n);g=ctypes.c_size_t()
 if not k.ReadProcessMemory(h,x,b,n,ctypes.byref(g)) or g.value!=n:raise OSError(hex(x))
 return b.raw
def u(x):return struct.unpack('<I',read(x,4))[0]
def s(x):
 b=bytearray()
 for i in range(256):
  c=read(x+i,1)
  if c==b'\0':return b.decode('ascii','replace')
  b.extend(c)
 raise ValueError('unterminated name')
def find(name):
 q=u(0x2abd8e0+4*(sum((119+i)*ord(c) for i,c in enumerate(name.lower()))&1023));seen=set()
 while q:
  if q in seen or len(seen)>128:raise ValueError('invalid hash chain')
  seen.add(q)
  if s(u(q)).lower()==name.lower():return q
  q=u(q+0x48)
 return 0
def value(q):
 if not q:return None
 t=read(q+8,1)[0];raw=read(q+12,16)
 v=(bool(raw[0]) if t==0 else struct.unpack('<f',raw[:4])[0] if t==1 else struct.unpack('<i',raw[:4])[0] if t in (5,6) else s(struct.unpack('<I',raw[:4])[0]) if t==7 else raw.hex())
 return dict(pointer=hex(q),name=s(u(q)),type=t,flags=u(q+4),current=v)
try:
 if read(0x6217e0,7)!=bytes.fromhex('53568bf085f675'):raise ValueError('wrong C1 code/base')
 ix=u(0x6c3d2ac)
 if ix>1024:raise ValueError('bad cg index')
 cg=u(0x16d3b58+4*ix)^0x490b400c
 pairs=[]
 for num,name,g in [('1477','r_specularColorScale',0xcf401c),('1478','r_diffuseColorScale',0xcf410c),('1498','r_lightGridEnableTweaks',0xcf4270),('1500','r_lightGridIntensity',0xcf40dc),('1501','r_lightGridContrast',0xcf4188),('1619','sm_sunShadowScale',0xcf430c)]:
  q=u(g)
  if s(u(q))!=num:raise ValueError('renderer dvar identity mismatch')
  pairs.append(dict(renderer=value(q),friendly=value(find(name))))
 print(json.dumps(dict(pid=a.pid,commandTime=u(cg),pairs=pairs,limitation='Persistent dvars only; inactive values do not establish prior gameplay values. IW4 semantic labels are corroborating leads; exact C1 identities and pointer separation are directly read.'),indent=2))
finally:k.CloseHandle(h)
