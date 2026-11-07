import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
probe=[("packetEvent",0x67520),("netchanProcess",0x1A5960),("decodeMessage",0x6BF80),
       ("parseServerMessage",0x6E6A0),("parseGameState",0x6DEA0),("parseConfigStrings",0x6DB20),
       ("storeRawConfigString",0x6DAA0),("parseSnapshot",0x6D170),("parsePacketEntities",0x6C2F0),
       ("parsePacketClients",0x6CC60),("parsePacketAux",0x6C840),("parseMatchState",0x6D060),
       ("parsePlayerState",0x1A4230),("readDeltaField",0x1A27F0),("readDeltaEntity",0x1A3670),
       ("readFieldIndex",0x1A3250),("readBits",0x1A13A0),("readBit",0xC370),
       ("configChecksumCompare",0x6E06B),("playerStateFields",0x855F70)]
# build call-target index (offset==RVA convention)
idx={}
for i in range(len(d)-5):
    if d[i]==0xE8:
        rel=struct.unpack_from("<i",d,i+1)[0]
        t=(i+5+rel)&0xffffffff
        idx.setdefault(t,[]).append(i)
print("Direct-call targets (E8 rel32) resolved with offset==RVA convention")
print("%-24s %10s  %-42s %s" % ("name","probeRVA","call_sites(offsets pointing AT this RVA)","#"))
for n,r in probe:
    c=idx.get(r,[])
    print("%-24s %10X  %-42s %d" % (n,r, ", ".join("%X"%x for x in c[:8]) or "-", len(c)))
print()
# Also check what IS at exactly these RVAs in terms of enclosing function
def entries(lo,hi):
    out=[]
    for p in range(lo,hi):
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            out.append(p)
    return out
E={}
for lo,hi in [(0x60000,0x70000),(0x1A0000,0x1A6000),(0x4000,0x20000)]:
    for p in entries(lo,hi): E.setdefault(p,True)
ents=sorted(E)
def enclosing(r):
    best=None
    for e in ents:
        if e<=r: best=e
        else: break
    return best
print("Enclosing function entry (from int3-padding prologue scan):")
for n,r in probe:
    e=enclosing(r)
    print("  %-24s RVA=%08X  enclosing_entry=%s  delta=%s" % (n,r,("%X"%e if e else "-"),(r-e if e else "-")))
