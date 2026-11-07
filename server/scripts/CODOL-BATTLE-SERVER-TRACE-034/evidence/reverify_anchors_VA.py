import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
BASE=0x400000
print("file size = 0x%X (%d)" % (len(d),len(d)))
print("Convention (PROVEN): file_offset == VA  ->  to read VA v, use d[v].  RVA = v - 0x400000.")
print()
# Section table: RawPtr fields are VA-relative tables (identity), so also absolute-ish; note them.
pe=struct.unpack_from("<I",d,0x3C)[0]
nsec=struct.unpack_from("<H",d,pe+6)[0]
sizeopt=struct.unpack_from("<H",d,pe+20)[0]
opt=pe+24; so=opt+sizeopt
print("Section table (VA / VSize / RawPtr / RawSize):")
for i in range(nsec):
    o=so+40*i
    nm=d[o:o+8].rstrip(b'\x00'); nm="".join(chr(c) if 32<=c<127 else '?' for c in nm)
    vsz,va,rsz,raddr=struct.unpack_from("<IIII",d,o+8)
    print("  %-10s VA=%08X VSize=%08X RawPtr=%08X RawSize=%08X" % (nm,va,vsz,raddr,rsz))
print()
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("storeRawConfigString",0x46DAA0),("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),
         ("parsePacketClients",0x46CC60),("parsePacketAux",0x46C840),("parseMatchState",0x46D060),
         ("parsePlayerState",0x5A4230),("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),
         ("readFieldIndex",0x5A3250),("readBits",0x5A13A0),("readPrimitive5A14E0",0x5A14E0),
         ("readPrimitive5A1580",0x5A1580),("readBit",0x400C370),("configChecksumCompare",0x46E06B)]
print("%-24s %10s %10s  %-22s %s" % ("name","VA","RVA","prologue@VA","first12"))
for name,va in anchors:
    if va>=len(d): print("%-24s %10X %10X  OUT_OF_FILE" % (name,va,va-BASE)); continue
    f=d[va:va+12].hex()
    if d[va:va+3]==b"\x55\x8b\xec": pr="55 8b ec (prologue)"
    elif d[va:va+3]==b"\x6a\xff": pr="6a ff (hotpatch)"
    elif d[va:va+2]==b"\x8b\xff": pr="8b ff"
    elif d[va]==0x55: pr="55"
    elif d[va]==0xcc: pr="cc (padding)"
    else: pr=d[va:va+3].hex()
    print("%-24s %10X %10X  %-22s %s" % (name,va,va-BASE,pr,f))
