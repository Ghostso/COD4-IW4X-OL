import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def rd(va,n): return d[va-BASE:va-BASE+n]
def func_start(va, back=0x400):
    """nearest preceding address whose previous byte is 0xCC (padding) -> reliable function start"""
    for p in range(va, va-back, -1):
        if d[p-1-BASE]==0xCC or d[p-1-BASE]==0xC3 or d[p-1-BASE]==0xC2:
            return p
    return None
def is_prolog(va):
    b=rd(va,4)
    return b[:3] in (b"\x55\x8b\xec", b"\x6a\xff") or b[:2]==b"\x8b\xff" or b[:2]==b"\x55\x8b" or b[:1]==b"\x55"
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("configChecksumCompare",0x46E06B)]
print("%-22s %8s  %-10s %-10s %-8s %s" % ("name","VA","bytes@VA","func_start","delta","prolog@VA?"))
for name,va in anchors:
    fs=func_start(va)
    delta = (va-fs) if fs is not None else None
    print("%-22s %8X  %-10s %-10s %-8s %s" % (name,va,rd(va,4).hex(),
          ("%X"%fs if fs else "-"), (delta if delta is not None else "-"), is_prolog(va)))
