import pathlib,struct,collections,math,re
D=pathlib.Path("codoMP_client_shipRetail.exe").read_bytes(); IB=0x400000
SECS=[(0x1000,0x8A689A,0x1000,0x593000),(0x8A8000,0x16DA70,0x594000,0x16E000),(0xA16000,0xDBB1CC0,0x702000,0x62000),(0xE5C8000,0x31,0x764000,0x1000),(0xE5C9000,0x9228,0x765000,0xA000),(0xE5D3000,0x4000,0x76F000,0x2000),(0xE5D7000,0x82000,0x771000,0x6000)]
def r2o(r):
 for va,vs,rp,rs in SECS:
  if va<=r<va+max(vs,rs):
   o=rp+r-va
   return o if r-va<rs else None
def rd(va):
 o=r2o(va-IB)
 return struct.unpack_from("<I",D,o)[0] if o is not None else None
for name,rva,ln in [("tp3_0_tail",0x613000,0x4000),("table",0x8A8000,0x800),("shadow",0xA12944,0x76C),("v32_00590000",0x590000,0x4000)]:
 o=r2o(rva)
 if o is None: print(name,"raw absent"); continue
 b=D[o:o+ln]
 ent=-sum((c/len(b))*math.log2(c/len(b)) for c in collections.Counter(b).values())
 asc=sum(32<=x<127 or x in (9,10,13) for x in b)
 nul=b.count(0)
 print(name,"rva",hex(rva),"raw",hex(o),"len",len(b),"entropy",round(ent,3),"ascii_frac",round(asc/len(b),3),"nul_frac",round(nul/len(b),3),"dwords_as_ptrs",sum(IB<=struct.unpack_from("<I",b,i)[0]<IB+0xE659000 for i in range(0,len(b)-3,4)))
 runs=[m.group().decode("latin1","replace") for m in re.finditer(rb"[ -~]{6,}",b)]
 print(" ascii_runs",runs[:8])
vals=[rd(x) for x in range(0xCA8000,0xCA876C,4)]
t=[v for v in vals if IB<=v<IB+0xE659000]
print("target count",len(t),"unique",len(set(t)))
for i,v in enumerate(t[:80]):
 o=r2o((v-IB)-0x8A8000)
 if o is None: continue
 b=D[o:o+16]
 print("%3d slot=%08X val=%08X off=%07X b=%s ent=%.2f nul=%d asc=%d"%(i,0xCA8000+4*i,v,o,b.hex(),-sum((c/16)*math.log2(c/16) for c in collections.Counter(b).values()),b.count(0),sum(32<=x<127 for x in b)))


