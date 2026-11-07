import struct,collections,csv,itertools
from capstone import *
D=open(r"codoMP_client_shipRetail.exe","rb").read(); IB=0x400000
sh=struct.unpack_from("<I",D,0x3c)[0]; n=struct.unpack_from("<H",D,sh+6)[0]; opt=sh+24; oh=struct.unpack_from("<H",D,sh+20)[0]; o=opt+oh
SEC=[]
for i in range(n):
 h=o+40*i; name=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); ch=struct.unpack_from("<I",D,h+36)[0]; SEC.append(dict(i=i,name=name,va=va,vs=vs,rs=rs,pr=pr,ch=ch))
def sec(rva):
 for s in SEC:
  if s["va"]<=rva<s["va"]+max(s["vs"],s["rs"]):return s
 return None
def off(rva):
 s=sec(rva)
 if not s:return None
 q=rva-s["va"];return s["pr"]+q if 0<=q<s["rs"] else None
def rd32(rva):
 f=off(rva);return None if f is None or f+4>len(D) else struct.unpack_from("<I",D,f)[0]
def is_exec(rva):
 s=sec(rva);return bool(s and s["name"]!=".tvm0" and s["ch"]&0x20000000 and off(rva) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
SLOTS=[0xca8114,0xca8194,0xca812c,0xca819c,0xca8164]
# raw refs
refs=[]
for s in SEC:
 if s["name"]==".tvm0":continue
 b=D[s["pr"]:s["pr"]+s["rs"]]
 for j in range(len(b)-6):
  if b[j]==0xff and b[j+1] in (0x15,0x25) and struct.unpack_from("<I",b,j+2)[0] in SLOTS:
   refs.append((s["va"]+j,struct.unpack_from("<I",b,j+2)[0],b[j+1]))
# strong function start candidates: ordered common prologues, plus aligned export RVAs
prologues=[b"\x55\x8b\xec",b"\x55\x89\xe5",b"\x8b\xff\x55\x8b\xec",b"\x64\xa1\x00\x00\x00\x00",b"\x6a\xff\x68"]
# export roots
exp_rva,exp_sz=struct.unpack_from("<II",D,opt+96); nf=struct.unpack_from("<I",D,off(exp_rva)+24)[0]; af=struct.unpack_from("<I",D,off(exp_rva)+28)[0]
exports=set()
for i in range(nf):
 r=struct.unpack_from("<I",D,off(af)+4*i)[0]
 if is_exec(r):exports.add(r)
# direct E8 target candidates restricted to exec
e8targets=collections.Counter()
for s in SEC:
 if s["name"]==".tvm0":continue
 b=D[s["pr"]:s["pr"]+s["rs"]]
 for j in range(len(b)-4):
  if b[j]==0xe8:
   t=s["va"]+j+5+struct.unpack_from("<i",b,j+1)[0]
   if is_exec(t):e8targets[t]+=1
starts=set(exports)
for s in SEC:
 if s["name"]==".tvm0":continue
 b=D[s["pr"]:s["pr"]+s["rs"]]
 for p in prologues:
  pos=0
  while True:
   q=b.find(p,pos)
   if q<0:break
   starts.add(s["va"]+q);pos=q+1
# only plausible starts near references; decode to ref
cache={}
def decode_to(start,ref):
 key=(start,ref)
 if key in cache:return cache[key]
 f=off(start); s=sec(start); target=ref
 if f is None or not is_exec(start) or not is_exec(ref):cache[key]=(False,"badmap",0);return cache[key]
 lim=min(0x8000, s["vs"]-(start-s["va"]), len(D)-f)
 ins=list(md.disasm(D[f:f+lim],IB+start))
 pc=IB+start; cnt=0; reason="end"
 for x in ins:
  if x.address==IB+ref:cache[key]=(True,"reached",cnt);return cache[key]
  if x.address>IB+ref:reason="passed";break
  pc=x.address+x.size;cnt+=1
  if x.mnemonic in ("ret","retn","iret","iretd","ud2","int3"):reason="term:"+x.mnemonic;break
  if x.mnemonic=="jmp":reason="term:jmp";break
 cache[key]=(False,reason,cnt);return cache[key]
# cluster by sorted ref gap > 0x10000 starts new cluster
allr=sorted(refs)
gaps=[]
clusters={}
for i,(r,slot,opc) in enumerate(allr):
 if i==0 or r-allr[i-1][0]>0x10000: cid=r
 clusters[r]=cid
rows=[]
for r,slot,opc in allr:
 cands=sorted([x for x in starts if 0<r-x<=0x2000],key=lambda x:r-x)
 checks=[(x,)+decode_to(x,r) for x in cands]
 ok=[x for x in checks if x[1]]
 z=next(md.disasm(D[off(r):off(r)+15],IB+r,count=1),None)
 nearby=[(rr,ss) for rr,ss,oo in allr if rr!=r and abs(rr-r)<=64]
 rows.append(dict(ref_rva="0x%08X"%r,slot="0x%08X"%slot,opcode="FF%02X"%opc,cluster="0x%08X"%clusters[r],self_decode=z.bytes.hex() if z else "",near_slots=" ".join("%s@%+d"%(("0x%08X"%ss),rr-r) for rr,ss in nearby),near_funcs=" ".join("%s/%s/%d"%("0x%08X"%x,reason,cnt) for x,okf,reason,cnt in checks[:5]),func_ok=len(ok)))
with open(r"scripts/_out/high_reuse_slot_callers.csv","w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
print("TOTAL REFS",len(allr))
print("SELF DECODE",sum(bool(x["self_decode"]) for x in rows))
print("FUNC-REACHED REFS",sum(x["func_ok"]>0 for x in rows))
print("CLUSTERS",len(set(x["cluster"] for x in rows)))
print("CO-SLOT <=64",[(x["ref_rva"],x["slot"],x["near_slots"]) for x in rows if x["near_slots"]])
for slot in SLOTS:
 rs=[x for x in rows if x["slot"]=="0x%08X"%slot]
 print("=== %08X value=%08X refs=%d func_ok=%d clusters=%s"%(slot,rd32(slot-IB),len(rs),sum(x["func_ok"]>0 for x in rs),collections.Counter(x["cluster"] for x in rs)))
 for x in rs:
  print(x["ref_rva"],"cluster",x["cluster"],"near",x["near_slots"] or "-","funcs",x["near_funcs"] or "-")
