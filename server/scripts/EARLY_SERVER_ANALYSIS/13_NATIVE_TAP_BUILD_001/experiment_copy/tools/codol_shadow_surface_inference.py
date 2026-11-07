"""Passive camera plus offline native collision-plane/triangle ray intersection.
This is an inferred collision surface, NOT a renderer hit or engine raycast.
No process writes, input, hooks, or calls into either engine.
"""
import argparse,ctypes,struct,json,math
from codol_shadow_probe import inspect
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--client",type=int,required=True);p.add_argument("--server",type=int,required=True);p.add_argument("--cm",type=lambda x:int(x,0),required=True);p.add_argument("--camera-capture",type=__import__("pathlib").Path);a=p.parse_args()
if a.camera_capture:
 raw=a.camera_capture.read_bytes();c=json.loads(raw.decode("utf-16" if raw.startswith(b"\xff\xfe") else "utf-8-sig"));c["viewAxes"]=c["cameraAxes"]
else:c=inspect(a.client)
if not c["hasPredictedGameplayState"]:raise SystemExit("No active camera")
k=ctypes.WinDLL("kernel32",use_last_error=True);k.OpenProcess.restype=ctypes.c_void_p;k.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.CloseHandle.argtypes=[ctypes.c_void_p]
h=k.OpenProcess(16,0,a.server)
def read(x,n):
 b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
 if not k.ReadProcessMemory(h,x,b,n,ctypes.byref(got)) or got.value!=n:raise OSError(hex(x))
 return b.raw
def u(x):return struct.unpack("<I",read(x,4))[0]
def dot(x,y):return sum(a*b for a,b in zip(x,y))
def sub(x,y):return [a-b for a,b in zip(x,y)]
def cross(x,y):return [x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]
try:
 name=read(u(a.cm),128).split(b"\0",1)[0].decode("latin1")
 if "killhouse" not in name:raise ValueError("Different native map")
 vc,vp,tc,tp=struct.unpack("<4I",read(a.cm+0x58,16))
 if vc>1000000 or tc>1000000:raise ValueError("Invalid collision counts")
 vertices=list(struct.iter_unpack("<3f",read(vp,vc*12)))
 triangles=list(struct.iter_unpack("<3H",read(tp,tc*6)))
 origin=c["viewOrigin"];direction=c["viewAxes"][:3];hits=[]
 for index,ids in enumerate(triangles):
  if max(ids)>=vc:raise ValueError("Invalid collision index")
  v0,v1,v2=[vertices[i] for i in ids];e1=sub(v1,v0);e2=sub(v2,v0);q=cross(direction,e2);det=dot(e1,q)
  if abs(det)<1e-8:continue
  s=sub(origin,v0);uu=dot(s,q)/det
  if uu<0 or uu>1:continue
  z=cross(s,e1);vv=dot(direction,z)/det
  if vv<0 or uu+vv>1:continue
  distance=dot(e2,z)/det
  if distance>0.1:hits.append(dict(kind="collision triangle",index=index,distance=distance,point=[origin[i]+distance*direction[i] for i in range(3)]))
 bc=struct.unpack("<H",read(a.cm+0x8c,2))[0];bp=u(a.cm+0x90)
 brushes=read(bp,bc*80)
 for index in range(bc):
  row=brushes[index*80:(index+1)*80];mins=struct.unpack_from("<3f",row);contents=struct.unpack_from("<I",row,12)[0];maxs=struct.unpack_from("<3f",row,16);ns,sp=struct.unpack_from("<2I",row,28)
  if not contents&1:continue
  if ns>65536:raise ValueError("Invalid brush sides")
  planes=[]
  for axis in range(3):
   n=[0,0,0];n[axis]=1;planes.append((n,maxs[axis]));n=[0,0,0];n[axis]=-1;planes.append((n,-mins[axis]))
  for j in range(ns):
   plane=struct.unpack("<4f",read(u(sp+12*j),16));planes.append((plane[:3],plane[3]))
  enter=0.;leave=100000.;normal=None
  for n,d in planes:
   den=dot(n,direction);dist=d-dot(n,origin)
   if abs(den)<1e-9:
    if dist<0:leave=-1;break
    continue
   t=dist/den
   if den<0 and t>enter:enter=t;normal=n
   elif den>0:leave=min(leave,t)
   if enter>leave:break
  if enter<=leave and enter>0.1:hits.append(dict(kind="solid collision brush",index=index,distance=enter,normal=normal,point=[origin[i]+enter*direction[i] for i in range(3)]))
 print(json.dumps(dict(client=a.client,server=a.server,map=name,commandTime=c["commandTime"],origin=origin,direction=direction,vertexCount=vc,triangleCount=tc,inferredHits=sorted(hits,key=lambda h:h["distance"])[:8],limitation="Offline collision triangle/solid-brush intersections; dynamic transforms and renderer-only surfaces omitted. Not an exact artifact wall hit."),indent=2))
finally:k.CloseHandle(h)
