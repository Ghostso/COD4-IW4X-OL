import glob, struct, os
dumps = sorted(glob.glob(r"run_codol_001\runs\ENGINE_DUMP_*\engine\engine_best.bin"))
print("dumps:", len(dumps))
if not dumps:
    raise SystemExit("no dump")
dump = max(dumps, key=os.path.getmtime)
d=open(dump,"rb").read()
print("using", dump, len(d))
RVA_BASE=0x594000; IB=0x400000; DUMPBASE=IB+RVA_BASE  # 0x994000
# target string VAs (exe)
targets={
 "IIPS\\iips.dll":0x00DB53F0,
 "iips.ini":0x00DC7E44,
 "enable_iips=%d":0x00DC7E50,
 "iips_url=%s":0x00DC7E60,
 "iips_listpackages":0x00AC8860+0x314000 if False else None,
}
# recompute VA properly: VA = file_off + 0x714000 for that section
def va(fo): return fo + 0x714000
for name,fo in [("IIPS\\iips.dll",0x6B53F0),("iips.ini",0x6C7E44),("enable_iips=%d",0x6C7E50),
                ("iips_url=%s",0x6C7E60),("iips_listpackages",0x6AC860),("iips_syncpackage",0x6AC874),
                ("iips_syncfile",0x6AC888),("AS_IIPS_IsPackReady",0x6B7EE4),("AS_IIPS_RequestPack",0x6B7EF8)]:
    targets[name]=va(fo)
for name,v in targets.items():
    print("%-24s VA 0x%08X"%(name,v))
print()
for name,v in targets.items():
    if v < DUMPBASE: 
        print("%-24s VA 0x%08X  (低于 dump 基址 0x%08X，dump 不覆盖)"%(name,v,DUMPBASE)); continue
    off = v - DUMPBASE
    if off+4 > len(d):
        print("%-24s VA 0x%08X  (超出 dump)"%(name,v)); continue
    le = struct.pack("<I", v)
    hits=[]; i=0
    while True:
        j=d.find(le,i)
        if j<0: break
        hits.append(j); i=j+1
    print("%-24s VA 0x%08X  dump内 4字节引用=%d  %s"%(name,v,len(hits),[hex(x) for x in hits[:8]]))
