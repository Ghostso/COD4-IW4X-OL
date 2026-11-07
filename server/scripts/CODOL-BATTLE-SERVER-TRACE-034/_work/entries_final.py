import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def rd(rva,n): return d[rva:rva+n]
def entry_back(rva, back=0x800):
    """nearest preceding address where a prologue follows padding/ret (reliable entry)"""
    best=None
    for p in range(rva, rva-back, -1):
        if p<=0: break
        b=rd(p,1)
        if b in (b"\x55", b"\x6a", b"\x8b") :
            pv=rd(p-1,1)
            if pv in (b"\xcc",b"\xc3",b"\xc2",b"\xcb"):
                if rd(p,3) in (b"\x55\x8b\xec",) or rd(p,2) in (b"\x6a\xff",b"\x8b\xff",b"\x55\x8b") or b==b"\x55":
                    return p
    # fallback nearest 55 8b ec
    for delta in range(0, back):
        for p in (rva-delta, rva+delta):
            if p>0 and rd(p,3)==b"\x55\x8b\xec": return p
    return None
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("configChecksumCompare",0x46E06B),("typeDispatchA",0x45F89B),
         ("typeDispatchB",0x4601A4),("oobDispatcher",0x5C071E)]
print("Convention (proven by string test): FILE OFFSET = RVA = VA - 0x400000")
print("%-22s %10s %10s %-9s %-6s %s" % ("name","VA","RVA","file@RVA","delta","entry_found"))
for n,va in anchors:
    rva=va-BASE
    e=entry_back(rva)
    print("%-22s %10X %10X %-9s %-6s %s" % (n,va,rva,rd(rva,4).hex(),
        (rva-e if e else "-"), ("%X(VA %X)"%(e,e+BASE) if e else "-")))
