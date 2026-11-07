import struct,math,collections,csv
d=open(r"codoMP_client_shipRetail.exe","rb").read(); ib=0x400000
secs=[(".tp3",0x1000,0x8a689a,0x593000,0x1000),(".tp3",0x8a8000,0x16da70,0x16e000,0x594000),(".tp3",0xa16000,0xdbb1cc0,0x62000,0x702000),(".tp3",0xe5c8000,0x31,0x1000,0x764000),(".tp3",0xe5c9000,0x9228,0xa000,0x765000),(".tvm0",0xe5d3000,0x4000,0x2000,0x76f000),(".tp3",0xe5d7000,0x82000,0x6000,0x771000)]
def off(rva):
 for t,va,vs,rs,pr in secs:
  if va<=rva<va+min(vs,rs): return pr+rva-va
 return None
def ent(b):
 if not b:return 0.0
 c=collections.Counter(b);return -sum((v/len(b))*math.log2(v/len(b)) for v in c.values())
print("target raw mapping",off(0x613000),off(0x615fff))
src=off(0x8a8000)
print("source template entropy %.4f"%ent(d[src:src+0x76c]))
for start in [0x590000,0x591000,0x592000,0x593000]:
 f=off(start)
 if f is None: print("window",hex(start),"NO_RAW"); continue
 b=d[f:f+0x1000]
 ptrs=sum(ib<=struct.unpack_from("<I",b,i)[0]<ib+0xe659000 for i in range(0,len(b)-3,4))
 print("window",hex(start),"entropy",round(ent(b),3),"nul",round(b.count(0)/len(b),3),"ascii",round(sum(32<=x<127 for x in b)/len(b),3),"ptrs",ptrs)
rows=list(csv.DictReader(open(r"scripts/_out/ca8000_boundary_audit.csv",newline="")))
cnt=collections.Counter(); refs=0
for r in rows:
 for x in filter(None,r["caller_rvas"].split()): cnt[int(x,16)]+=1; refs+=1
print("raw caller refs",refs,"unique callers",len(cnt))
print("top callers",[(hex(k),v) for k,v in cnt.most_common(30)])
print("caller high16",[(hex(k),v) for k,v in collections.Counter(k>>16 for k in cnt).most_common(20)])
known={0x363f0,0x36460,0x36470,0x36480,0x36490,0x364a0,0x364f0,0x36510,0x36520,0x36570,0x365e0,0x36790,0x367a0,0x3a180,0x3a1a0,0x3a1d0,0x3a200,0x3a220,0x255220}
print("callers inside named export bodies",[(hex(k),v) for k,v in cnt.items() if k in known])
