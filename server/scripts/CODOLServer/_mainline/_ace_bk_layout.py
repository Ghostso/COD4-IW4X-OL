import pefile, os, math, collections, json

BK = r"backups\ACE_FULL_20260925_184421\files"
rows=[]
for dp,_,fns in os.walk(BK):
    for fn in fns:
        p=os.path.join(dp,fn)
        try:
            d=open(p,"rb").read()
        except: continue
        if d[:2]!=b"MZ": 
            rows.append({"file":fn,"size":len(d),"kind":"non-PE"}); continue
        try:
            pe=pefile.PE(p, fast_load=True)
        except Exception as e:
            rows.append({"file":fn,"size":len(d),"kind":"PE?err="+str(e)[:40]}); continue
        secs=[]
        for s in pe.sections:
            nm=s.Name.rstrip(b"\x00").decode("latin1")
            seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData][:0x20000]
            if seg:
                c=collections.Counter(seg); tot=len(seg)
                ent=-sum((v/tot)*math.log2(v/tot) for v in c.values())
            else: ent=0.0
            secs.append("%s:%.1f"%(nm,ent))
        rows.append({"file":fn,"size":len(d),
                     "machine":hex(pe.FILE_HEADER.Machine),
                     "ib":hex(pe.OPTIONAL_HEADER.ImageBase),
                     "ep":hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
                     "secs":",".join(secs),
                     "dll": bool(pe.FILE_HEADER.Characteristics & 0x2000)})
json.dump(rows, open(r"CODOLServer\_mainline\_ace_bk_layout.json","w"), indent=1)
print("%-46s %10s %6s %-10s %-9s %s"%("file","size","mach","imagebase","entry","sections(entropy)"))
for r in sorted(rows, key=lambda x:-x["size"]):
    if "secs" in r:
        print("%-46s %10d %6s %-10s %-9s %s"%(r["file"][:46], r["size"], r["machine"].replace("0x",""), r["ib"], r["ep"], r["secs"]))
    else:
        print("%-46s %10d  %s"%(r["file"][:46], r["size"], r.get("kind","")))
