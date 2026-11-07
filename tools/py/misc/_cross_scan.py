from pathlib import Path
root=Path("COD OL")
pat=bytes.fromhex("68f45ecd01ff151481ca00a1fc5ecd0185c0790e8b15f85ecd015052ff159481ca00")
alt=bytes.fromhex("a1fc5ecd0185c0790e8b15f85ecd015052ff159481ca00")
for p in root.iterdir():
 if not p.is_file(): continue
 try: d=p.read_bytes()
 except: continue
 for q in (pat,alt):
  i=d.find(q)
  if i>=0: print(p.name,hex(i),q.hex()[:16])

