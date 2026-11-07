IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
def nearest_prologue(off, span=0x800):
    best=None
    for delta in range(0, span):
        for s in (off-delta, off+delta):
            if 0 <= s < len(d)-3 and d[s:s+3]==b"\x55\x8b\xec":
                return s, s-off
    return None,None
print("anchor RVA -> nearest 55 8b ec prologue, under two offset interpretations")
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0)]
print("%-20s | %-14s %-10s | %-14s %-10s" % ("name","off=RVA","delta","off=RVA-0x400000","delta"))
for name,n in anchors:
    a,da = nearest_prologue(n)
    b,db = nearest_prologue(n-0x400000)
    print("%-20s | %-14s %-10s | %-14s %-10s" % (name,
        ("%X"%a if a is not None else "-"), (da if da is not None else "-"),
        ("%X"%b if b is not None else "-"), (db if db is not None else "-")))
