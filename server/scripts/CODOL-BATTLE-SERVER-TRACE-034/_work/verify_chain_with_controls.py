import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail=False
def clean_run(rva, limit=120):
    """count instructions decoded before hitting an invalid byte; return (n, terminator_seen)"""
    n=0; ret=False
    for ins in md.disasm(d[rva:rva+400], rva):
        n+=1
        if ins.mnemonic in ("ret","retf") or ins.mnemonic.startswith("ret"): ret=True; break
        if n>=limit: break
    return n, ret
def prev_boundary(rva, back=0x1000):
    for p in range(rva, rva-back, -1):
        if p<=0: break
        if d[p-1]==0xCC and d[p:p+3]==b"\x55\x8b\xec": return p
    return None
def report(name,va,control=False):
    rva=va-BASE
    if not (0 <= rva < len(d)):
        print("%-24s VA=%08X RVA=%08X  ** OUT OF IMAGE **" % (name,va,rva)); return
    n,ret=clean_run(rva)
    pb=prev_boundary(rva)
    tag="CONTROL" if control else ""
    print("%-24s VA=%08X RVA=%08X  byte0=%02x  decode_insns=%-4d ret=%-5s nearest_pad_prolog=%s(d=%s) %s"
          % (name,va,rva,d[rva],n,ret,
             ("%X"%pb if pb else "-"), (rva-pb if pb else "-"), tag))
print("=== CONTROLS: TASK-031 anchors PROVEN to be real functions in this image ===")
for n,va in [("accepted_parser_0x632680",0x632680),("mmstart_ctor_0x632070",0x632070),
             ("latch_consumer_0x634340",0x634340),("accepted_cmp_0xC3C678",0xC3C678)]:
    report(n,va,control=True)
print()
print("=== TASK-009 battle chain anchors (as listed) ===")
b=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
   ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
   ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
   ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
   ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
   ("readBits",0x5A13A0),("storeRawConfigString",0x46DAA0),("configChecksumCompare",0x46E06B)]
for n,va in b: report(n,va)
