import glob, os, re
zero=set(); nonzero=set()
for p in glob.glob(r"run_codol_001\runs\*\launch.txt"):
    try: t=open(p,encoding="utf-8",errors="replace").read()
    except Exception: continue
    m=re.search(r"logs\\(E57A5C_[0-9_a-z]+)\\ready\.flag", t)
    name=m.group(1) if m else None
    if not name: continue
    if "force-p608-zero-key" in t: zero.add(name)
    else: nonzero.add(name)
print("zero-key runs:", len(zero))
for n in sorted(zero): print("   ", n)
print()
# check which of the 9 decodable ones are in zero set
dec=["E57A5C_20261001_202115_a2","E57A5C_20261001_203723_a1","E57A5C_20261001_204530_a1",
     "E57A5C_20261001_210604_a2","E57A5C_20261001_211039_a1","E57A5C_20261001_211600_a2",
     "E57A5C_20261001_212007_a1","E57A5C_20261001_213100_a1","E57A5C_20261001_213928_a1"]
print("decodable-run -> zero-key flag:")
for d in dec:
    print("   %s  zero=%s" % (d, d in zero))
