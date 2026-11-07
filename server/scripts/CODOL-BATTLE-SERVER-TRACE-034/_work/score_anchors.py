import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("readBit",0x400C370)]
def score(off):
    """return (prologue_ok, has_ret_within_4k, first6)"""
    if off is None or off < 0 or off+0x1000 > len(d): return (False,False,"OOR")
    first = d[off:off+6]
    prologue = first[:3] in (b"\x55\x8b\xec",) or first[:2]==b"\x55\x8b" or first[0]==0x55
    seg = d[off:off+0x1000]
    has_ret = (b"\xc3" in seg or b"\xc2" in seg)
    return (prologue, has_ret, first.hex())
print("%-22s | %-28s | %-28s" % ("anchor(VA?)","off = n (as RVA)","off = n-0x400000 (as VA)"))
a_score=b_score=0
for name,n in anchors:
    sa=score(n); sb=score(n-0x400000)
    a_score += (1 if sa[0] else 0); b_score += (1 if sb[0] else 0)
    print("%-22s | %-6s %-6s %-12s | %-6s %-6s %-12s" % (name, sa[0],sa[1],sa[2], sb[0],sb[1],sb[2]))
print()
print("prologue-score: off=n -> %d ; off=n-0x400000 -> %d" % (a_score,b_score))
