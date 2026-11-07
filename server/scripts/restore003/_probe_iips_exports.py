"""Ad-hoc: dump the ORIGINAL iips.dll export directory, verbatim."""
import struct
import sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
p = ROOT + r"\COD OL\IIPS\iips.dll"
d = open(p, "rb").read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
dirs = struct.unpack_from("<16I", d, pe + 24 + 96)
erva = dirs[0]
o = erva
name_rva, base, nfn, nn = struct.unpack_from("<IIII", d, o + 12)
aof, aon, aoo = struct.unpack_from("<III", d, o + 28)
print("EXPORT dir RVA=0x%X size=%d fileoff=0x%X" % (erva, dirs[1], o))
print("  Name RVA=0x%X Base=%d nfunc=%d nnames=%d" % (name_rva, base, nfn, nn))
print("  AOF=0x%X AON=0x%X AOO=0x%X" % (aof, aon, aoo))
print("  len(file)=0x%X" % len(d))
e = d.index(b"\x00", name_rva)
print("  dll name = %r" % d[name_rva:e].decode("latin1"))
print()
print("  AddressOfFunctions table (nfunc=%d):" % nfn)
for i in range(nfn):
    off = aof + i * 4
    fr = struct.unpack_from("<I", d, off)[0]
    print("    func[%d] @fileoff 0x%X = RVA 0x%X" % (i, off, fr))
print("  AddressOfNames table (nnames=%d):" % nn)
for i in range(nn):
    off = aon + i * 4
    nr = struct.unpack_from("<I", d, off)[0]
    inb = nr < len(d)
    nm = ""
    if inb:
        try:
            e2 = d.index(b"\x00", nr)
            nm = d[nr:e2].decode("latin1")
        except Exception:
            nm = "<unreadable>"
    print("    name[%d] @fileoff 0x%X = nameRVA 0x%X inb=%s %r" % (i, off, nr, inb, nm))
print("  AddressOfNameOrdinals table (nnames=%d):" % nn)
for i in range(nn):
    off = aoo + i * 4
    raw4 = d[off:off + 4]
    lo = struct.unpack_from("<H", d, off)[0]
    hi = struct.unpack_from("<H", d, off + 2)[0]
    print("    ord[%d] @fileoff 0x%X bytes=%s lo=%d hi=%d" % (i, off, raw4.hex(" ").upper(), lo, hi))
print()
print("  ==> Note: this table is 2-byte entries (WORD), so reading it as dwords")
print("      at +4 stride re-reads neighbours. Iterating with i*2 is correct.")
print()
for i in range(nn):
    off = aoo + i * 2
    no = struct.unpack_from("<H", d, off)[0]
    inb = no < nfn
    fr = struct.unpack_from("<I", d, aof + no * 4)[0] if inb else None
    nr = struct.unpack_from("<I", d, aon + i * 4)[0]
    e2 = d.index(b"\x00", nr)
    print("   %-28s nameIdx=%d ordArg=%d ord=%s funcRVA=%s" % (
        d[nr:e2].decode("latin1"), i, no, (no + base) if inb else "OOB",
        ("0x%X" % fr) if fr is not None else "OUT_OF_BOUNDS"))
print()
print("raw export dir bytes:", d[o:o + 40].hex(" ").upper())
sys.exit(0)
