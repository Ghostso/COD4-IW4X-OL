from pathlib import Path
import struct,collections
D=Path("codoMP_client_shipRetail.exe").read_bytes();IB=0x400000
SECS=[(".tp3#0",0x1000,0x8A689A,0x1000,0x593000),(".tp3#1",0x8A8000,0x16DA70,0x594000,0x16E000),(".tp3#2",0xA16000,0xDBB1CC0,0x702000,0x62000),(".tp3#3",0xE5C8000,0x31,0x764000,0x1000),(".tp3#4",0xE5C9000,0x9228,0x765000,0xA000),(".tvm0",0xE5D3000,0x4000,0x76F000,0x2000),(".tp3#6",0xE5D7000,0x82000,0x771000,0x6000)]
def cls(off):
 for n,va,vs,rp,rs in SECS:
  if rp<=off<rp+rs:return n,IB+va+off-rp
 return "header/?",None
print("SLOT_LITERAL_OCCURRENCES")
for val in [0xCA8000,0xCA8004,0xCA8100,0xCA812C,0xCA8164,0xCA818C,0xCA819C,0xCA84C8,0xCA875C]:
 p=struct.pack("<I",val);pos=[];s=0
 while True:
  i=D.find(p,s)
  if i<0:break
  pos.append(i);s=i+1
 print(hex(val),len(pos),[(hex(o),cls(o)) for o in pos[:40]])
vals=[struct.unpack_from("<I",D,0x594000+4*i)[0] for i in range(474)]
valsset={v for v in vals if IB<=v<IB+0xE659000}
occ=collections.Counter();slots=[]
for i in range(len(D)-3):
 v=struct.unpack_from("<I",D,i)[0]
 if v in valsset:
  occ[v]+=1
  if not (0x594000<=i<0x594000+0x76c) and not (0x6fe944<=i<0x6fe944+0x76c):slots.append((i,v))
print("TARGET_OCCURRENCES",len(valsset),dict(collections.Counter(occ.values())))
print("OUTSIDE_TEMPLATE",len(slots),len(set(v for _,v in slots)))
for i,v in slots[:120]:print(hex(i),hex(v))
print("LOW_NIBBLE",dict(collections.Counter(v&0xf for v in vals if IB<=v<IB+0xE659000)))
print("PAGES",[(hex(k<<12),v) for k,v in sorted(collections.Counter((v>>12) for v in vals if IB<=v<IB+0xE659000).items())])
print("FIRST_DELTAS")
for i,v in enumerate(vals[:30]):
 prev=vals[i-1] if i else None
 print(i,hex(v),hex(v-prev) if prev is not None and IB<=prev<IB+0xE659000 and v>=prev else "-")
s=Path("docs/game-net-hunt-report.md").read_text(encoding="utf-8")
for needle in ("dwLobbyEventHandler","0xCA8000","0xca8000","80000001"):
 print("DOC",needle)
 i=0
 while True:
  j=s.find(needle,i)
  if j<0:break
  print(s[max(0,j-200):min(len(s),j+400)].encode("ascii","replace").decode("ascii"))
  i=j+len(needle)
