import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG,'rb').read()
print("=== Convention test using a KNOWN string ===")
print("TASK-031 established: 'mmbook accepted' at VA 0xDC69B0 (read via offset VA-0x400000)")
for label, off in [("offset = VA-0x400000 = 0x9C69B0", 0x9C69B0), ("offset = VA = 0xDC69B0", 0xDC69B0)]:
    end = d.find(b'\x00', off)
    print("  %-34s -> %r" % (label, d[off:end][:32]))
print()
print("=== Convention test using 'mmstart sv_resetServer' (TASK-031: VA 0xDC6800) ===")
for label, off in [("VA-0x400000 = 0x9C6800", 0x9C6800), ("VA = 0xDC6800", 0xDC6800)]:
    end = d.find(b'\x00', off)
    print("  %-28s -> %r" % (label, d[off:end][:48]))
print()
print("=== Now re-resolve the B-layer anchors under BOTH conventions ===")
BASE=0x400000
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0)]
print("%-20s | %-28s | %-28s" % ("name","as VA: off=VA-0x400000","as fileoff: off=num"))
for name,n in anchors:
    a = d[n-BASE:n-BASE+10].hex()
    b = d[n:n+10].hex()
    print("%-20s | %s | %s" % (name, a, b))
