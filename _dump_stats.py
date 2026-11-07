import math,collections
from pathlib import Path
p=Path("COD OL/tqm/dump/GbDump.2.8975234.codomp_client_shipretail.exe.dmp.dat")
D=p.read_bytes()
def H(b):
 c=collections.Counter(b); n=len(b)
 return -sum(v/n*math.log2(v/n) for v in c.values())
print("len",len(D))
print("entropy",round(H(D),6))
print("unique_bytes",len(set(D)))
print("zero_ratio",round(D.count(0)/len(D),6))
print("ascii_ratio",round(sum(32<=x<127 for x in D)/len(D),6))
for bs in (16,32,64,256,1024):
 vals=[H(D[i:i+bs]) for i in range(0,len(D)-bs+1,bs)]
 print("block",bs,"min",round(min(vals),4),"mean",round(sum(vals)/len(vals),4),"max",round(max(vals),4))
print("prefix_sigs")
for sig in (b"MDMP",b"PAGEDUMP",b"PAGEDU64",b"MSCF",b"PK\x03\x04",b"MZ",b"\x7fELF"):
 print(sig,D.find(sig))
runs=[]; st=None
for i,x in enumerate(D):
 ok=32<=x<127
 if ok and st is None: st=i
 if not ok and st is not None:
  if i-st>=8: runs.append((st,i,D[st:i].decode("latin1")))
  st=None
print("printable_runs",runs[:30])
