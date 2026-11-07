import hashlib, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG,'rb').read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
mach, nsec, ts = struct.unpack_from("<HHI", d, pe+4)
sizeopt = struct.unpack_from("<H", d, pe+20)[0]
opt = pe + 24
imgbase = struct.unpack_from("<I", d, opt+28)[0]
sizeofimg = struct.unpack_from("<I", d, opt+56)[0]
so = opt + sizeopt          # <-- corrected
print("PE=%X nsec=%d sizeopt=%X sectbl=%X ImageBase=%X SizeOfImage=%X" % (pe,nsec,sizeopt,so,imgbase,sizeofimg))
secs=[]
for i in range(nsec):
    o = so + 40*i
    nm = d[o:o+8].rstrip(b'\x00')
    nm = "".join(chr(c) if 32<=c<127 else "?" for c in nm)
    vsz, va, rsz, raddr = struct.unpack_from("<IIII", d, o+8)
    ch = struct.unpack_from("<I", d, o+36)[0]
    secs.append((nm, va, vsz, raddr, rsz, ch))
    print("  %-9s VA=%08X VSize=%08X RawPtr=%08X RawSize=%08X ch=%08X" % (nm,va,vsz,raddr,rsz,ch))
def va_to(va):
    for nm,sva,vsz2,raddr2,rsz2,ch2 in secs:
        if sva <= va < sva + max(vsz2, rsz2): return raddr2 + (va-sva), nm
    return None,None
print()
anchors=[("packetEvent",0x467520),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80),
         ("parseServerMessage",0x46E6A0),("parseGameState",0x46DEA0),("parseConfigStrings",0x46DB20),
         ("parseSnapshot",0x46D170),("parsePacketEntities",0x46C2F0),("parsePacketClients",0x46CC60),
         ("parsePacketAux",0x46C840),("parseMatchState",0x46D060),("parsePlayerState",0x5A4230),
         ("readDeltaField",0x5A27F0),("readDeltaEntity",0x5A3670),("readFieldIndex",0x5A3250),
         ("readBits",0x5A13A0),("readBit",0x400C370)]
print("%-22s %8s %8s %-9s %8s %-8s %s" % ("name","VA","RVA","section","fileoff","inimg","first12"))
for name, va in anchors:
    off,sec = va_to(va)
    b = d[off:off+12].hex() if off is not None else "-"
    ok = "YES" if (off is not None and va < imgbase+sizeofimg) else "NO"
    print("%-22s %08X %08X %-9s %08X %-8s %s" % (name,va,va-imgbase,sec or "-",off or 0,ok,b))
