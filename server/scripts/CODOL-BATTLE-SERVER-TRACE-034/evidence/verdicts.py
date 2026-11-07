import struct, json
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def u32(off): return struct.unpack_from("<I",d,off)[0]
def entries(lo,hi):
    out=[]
    for p in range(lo,hi):
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            out.append(p)
    return out
ents=sorted(set(entries(0x4000,0x90000)) | set(entries(0x1A0000,0x1A6000)))
def enclosing(r):
    best=None
    for e in ents:
        if e<=r: best=e
        else: break
    return best
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("readBit",0x400C370),("configChecksumCompare",0x46E06B),
         ("storeRawConfigString",0x46DAA0)]
print("VERDICT TABLE (convention: file_offset = RVA = VA-0x400000)")
print("%-24s %10s %10s %-8s %-11s %-8s %s" % ("name","VA","RVA","in file","byte@RVA","entry?","note"))
for n,va in anchors:
    r=va-BASE
    infile = 0<=r<len(d)
    b = d[r] if infile else None
    e = enclosing(r) if infile else None
    prologue = (d[r:r+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[r:r+2]==b"\x8b\xff") if infile else False
    note = "starts a function" if prologue else ("MID-FUNCTION (not an entry)" if e else "-")
    print("%-24s %10X %10X %-8s %-11s %-8s %s" % (n,va,r,
        "YES" if infile else "NO", ("%02x"%b if b is not None else "-"),
        ("%X"%e if e is not None else "-"), note))
