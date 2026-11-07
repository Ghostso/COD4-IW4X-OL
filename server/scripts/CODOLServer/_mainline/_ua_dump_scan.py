import glob, os, struct, re
dumps=sorted(glob.glob(r"run_codol_001\runs\ENGINE_DUMP_*\engine\engine_best.bin"), key=os.path.getmtime)
dump=dumps[-1]; d=open(dump,"rb").read()
print("dump:",dump,len(d))
for magic in (b"FWS",b"CWS",b"ZWS",b"GFX",b"CFX"):
    i=0;h=[]
    while True:
        j=d.find(magic,i)
        if j<0: break
        h.append(j); i=j+1
        if len(h)>10: break
    print("%-4r -> %s"%(magic,[hex(x) for x in h]))
print("--- 含 ui_/menu_/sf_ 的可读串 ---")
seen=0
for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if low.startswith(("ui_","menu_","sf_","lui_")) or ".gfx" in low or "lobby" in low:
        print("   +0x%06X %r"%(m.start(), s[:100])); seen+=1
        if seen>40: break
