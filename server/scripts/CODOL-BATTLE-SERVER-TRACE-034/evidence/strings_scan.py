IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
needles=[b"getchallenge",b"connect\x00",b"gamestateupdate",b"heartbeat",b"challengeResponse",
         b"CL_ParseServerMessage",b"parseServerMessage",b"svc_",b"NETCHAN",b"netchan",
         b"reliable",b"snapshot\x00",b"configstring",b"gamestate\x00",b"CL_ParseSnapshot",
         b"packetEvent",b"packetEntities",b"baseline",b"delta\x00"]
print("%-24s %-10s %s" % ("needle","count","first offsets (VA)"))
for n in needles:
    offs=[]; s=0
    while True:
        i=d.find(n,s)
        if i<0: break
        offs.append(i+BASE); s=i+1
        if len(offs)>=6: break
    print("%-24s %-10d %s" % (n.decode('latin1'), len(offs), ["%X"%o for o in offs] or "-"))
