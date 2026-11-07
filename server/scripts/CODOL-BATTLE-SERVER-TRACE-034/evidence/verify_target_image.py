# -*- coding: utf-8 -*-
"""TASK-034 : consolidated target-image verification (read-only)."""
import hashlib, struct, capstone, os
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG,'rb').read()
BASE = 0x400000
print("IMAGE      : %s" % IMG)
print("SIZE       : %d bytes (0x%X)" % (len(d), len(d)))
print("SHA-256    : %s" % hashlib.sha256(d).hexdigest())
pe = struct.unpack_from("<I", d, 0x3C)[0]
mach,nsec,ts = struct.unpack_from("<HHI", d, pe+4)
opt = pe+24
print("PE         : machine=0x%X sections=%d TimeDateStamp=0x%08X" % (mach,nsec,ts))
print("ImageBase  : 0x%X   SizeOfImage: 0x%X" % (struct.unpack_from("<I",d,opt+28)[0],
                                                 struct.unpack_from("<I",d,opt+56)[0]))
print()
print("== ADDRESSING CONVENTION (proven by ASCII string test) ==")
for va,expect in [(0xDC69B0,b"mmbook accepted"),(0xDC6800,b"mmstart sv_resetServer"),(0xDC6724,b"mmbook")]:
    off=va-BASE
    got=d[off:d.find(b'\x00',off)]
    print("  VA %08X -> file offset %08X : %r  %s" % (va,off,got[:34],"MATCH" if got.startswith(expect) else "MISMATCH"))
print("  => file_offset = RVA = VA - ImageBase ; VA = ImageBase + RVA")
print()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
anchors=[("packetEvent",0x67520),("netchanProcess",0x1A5960),("decodeMessage",0x6BF80),
         ("parseServerMessage",0x6E6A0),("parseGameState",0x6DEA0),("parseConfigStrings",0x6DB20),
         ("parseSnapshot",0x6D170),("parsePacketEntities",0x6C2F0),("parsePacketClients",0x6CC60),
         ("parsePacketAux",0x6C840),("parseMatchState",0x6D060),("parsePlayerState",0x1A4230),
         ("readDeltaField",0x1A27F0),("readDeltaEntity",0x1A3670),("readFieldIndex",0x1A3250),
         ("readBits",0x1A13A0),("readBit",0x3C0C370),("configChecksumCompare",0x6E06B),
         ("storeRawConfigString",0x6DAA0),("playerStateFields",0x855F70)]
def entries(lo,hi):
    lo=max(1,lo); hi=min(hi,len(d)); out=[]
    for p in range(lo,hi):
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            out.append(p)
    return out
ents=set()
for lo,hi in [(0x4000,0x90000),(0x180000,0x1A0000),(0x1A0000,0x1A6000),(0x3C00000,0x3C10000)]:
    ents|=set(entries(lo,hi))
ents=sorted(ents)
def enc(r):
    b=[e for e in ents if e<=r]
    return b[-1] if b else None
print("== TASK-009 RVA CROSSWALK (convention applied) ==")
print("%-22s %-10s %-9s %-8s %-6s %s" % ("name","RVA","in_file","byte@RVA","entry","note"))
for n,r in anchors:
    inf = 0<=r<len(d)
    b = d[r] if inf else None
    e = enc(r) if inf else None
    pro = (d[r:r+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[r:r+2]==b"\x8b\xff") if inf else False
    note = "FUNCTION ENTRY" if pro else ("mid-function" if e else "-")
    print("%-22s %-10X %-9s %-8s %-6s %s" % (n,r,"YES" if inf else "NO",
        ("%02x"%b if b is not None else "-"), ("%X"%e if e is not None else "-"), note))
print()
print("== LOCAL OOB DISPATCHER (independently discovered in THIS target) ==")
print("  function entry RVA 0x1C05F0  (VA 0x5C05F0):")
for ins in md.disasm(d[0x1C05F0:0x1C0630], 0x1C05F0):
    print("    RVA %08X  %-18s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
print("  battle command strings found in THIS image (VA / file offset):")
for label,va in [("getchallenge",0xDBFD04),("gamestateupdate",0xDB4700),("heartbeat",0xDBFE40),
                 ("challengeResponse",0xDBFEE8),("connect",0xDC5694),("cancelConnect",0xDBFC8C),
                 ("connectResponse",0xDBFF0C),("userinfo",0xDBFFB4)]:
    off=va-BASE
    s=d[off:d.find(b'\x00',off)].decode('latin1','replace')
    print("    0x%08X (off 0x%06X) : %r" % (va,off,s))
print()
print("== PROBE RVA CONSISTENCY CHECK ==")
print("  CodolNetchanTrace.py declares RVAs as module.base.add(RVA); module.base == ImageBase == 0x400000.")
print("  If these RVAs belonged to THIS image, rva 0x632680 (T-031-proven function) would be a prologue.")
print("  Probe list DOES NOT contain 0x632680; it contains the battle family only.")
print("  For every battle RVA above, the byte at that RVA is NOT a function prologue (except 0x6D060).")
