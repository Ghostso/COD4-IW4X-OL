import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def rd(va,n): return d[va-BASE:va-BASE+n]
def entry(va, back=0x1000):
    """scan back for a prologue preceded by padding/ret"""
    p=va
    while p > va-back:
        b=rd(p,1)
        prev=rd(p-1,1)
        if b in (b"\x55",) and prev in (b"\xcc",b"\xc3"):
            return p
        p-=1
    return None
for name, va in [("OOB dispatcher (getchallenge site)",0x5C0600),
                 ("type dispatcher A (0x45F89B)",0x45F860),
                 ("type dispatcher B (0x4601A4)",0x460170),
                 ("parseServerMessage-ish (0x46E6D0)",0x46E6D0),
                 ("parseSnapshot-ish (0x46D190)",0x46D190),
                 ("parsePacketEntities region (0x46C2F0)",0x46C2F0),
                 ("readDeltaField region (0x5A2760)",0x5A2760)]:
    e=entry(va)
    print("%-38s site=%08X  entry=%s  delta=%s" % (name,va,("%08X"%e if e else "-"),(va-e if e else "-")))
