import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def rd(va,n): return d[va-BASE:va-BASE+n]
def find_func_start(va, back=0x200):
    """scan backwards for 55 8b ec / 6a ff / 8b ff that is followed by a plausible body"""
    for delta in range(0, back):
        p=va-delta
        if p-BASE < 0: break
        b=rd(p,3)
        if b[:3]==b"\x55\x8b\xec" or b[:3]==b"\x6a\xff" or b[:2]==b"\x8b\xff":
            # require that the instruction before p is a terminator (ret/int3/jmp/nop-ish) OR p is a known entry
            before=rd(p-1,1)
            if before in (b"\xc3", b"\xcc", b"\xc2", b"\xe9", b"\xeb") or p==va:
                return p, delta, b
    # fallback: nearest prologue regardless
    for delta in range(0, back):
        for p in (va-delta, va+delta):
            if p-BASE<0: continue
            b=rd(p,3)
            if b[:3]==b"\x55\x8b\xec": return p, delta, b
    return None,None,None
print("Re-verified B-layer anchors on image_best.bin (file_offset = VA - 0x400000)")
print("VA = 0x400000 + RVA ; ImageBase=0x400000 ; SizeOfImage=0xE659000")
print()
print("%-22s %10s %10s %-9s %-10s %-8s %s" % ("name","VA","RVA","in_image","func_start","delta","first bytes @VA"))
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("configChecksumCompare",0x46E06B),("expectedConfigChecksum",0x69F7D90)]
for name,va in anchors:
    inimg = va < BASE+0xE659000
    if da:=None: pass
    try:
        fs,delta,b = find_func_start(va)
        print("%-22s %10X %10X %-9s %-10s %-8s %s" % (name,va,va-BASE,"YES" if inimg else "NO",
              ("%X"%fs if fs else "-"), (delta if delta is not None else "-"), rd(va,12).hex()))
    except Exception as e:
        print("%-22s %10X %10X %-9s ERR %s" % (name,va,va-BASE,"YES" if inimg else "NO",e))
