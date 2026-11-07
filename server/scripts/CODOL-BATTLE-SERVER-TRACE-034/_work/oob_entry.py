IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
print("=== OOB dispatcher true entry check ===")
for va in (0x5C05F0,0x5C0600,0x5C0700,0x5C070E,0x5C0776,0x5C0E07,0x5C0EBB):
    print("  RVA %X : %s" % (va-BASE, d[va-BASE:va-BASE+16].hex()))
print()
print("=== does the OOB dispatcher reference 'getchallenge'/'connect' as push imm32? already shown ===")
print("=== search for other battle-related strings in the target ===")
for s in [b"connectResponse",b"challengeResponse",b"getInfo",b"getchallenge",b"heartbeat",
          b"cancelConnect",b"stats",b"rcon",b"statusResponse",b"gamestate",b"configstring",
          b"snapshot",b"userinfo",b"sv_",b"cl_",b"CL_"]:
    o=[]; st=0
    while True:
        i=d.find(s,st)
        if i<0: break
        o.append(i); st=i+1
        if len(o)>=5: break
    print("  %-20s count(first5)=%d  %s" % (s.decode('latin1'),len(o),["%X"%(x) for x in o]))
