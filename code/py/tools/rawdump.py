#!/usr/bin/env python3
"""读任意 file 偏移的原始字节 + 尝试多种解释."""
import struct, sys
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(f):
    e = d.find(b"\x00", f); return d[f:e] if e>f else b''
for a in sys.argv[1:]:
    f = int(a, 0)
    raw = d[f:f+32]
    out("--- file 0x%06X (VA 0x%06X) ---" % (f, f+VA))
    out("  raw   : " + raw.hex(" "))
    out("  u32x8 : " + " ".join("%08X" % x for x in struct.unpack_from("<8I", d, f)))
    out("  as f32: 4 x f32 = " + repr(struct.unpack_from("<4f", d, f)))
    out("  as u64: " + " ".join("%016X" % x for x in struct.unpack_from("<4Q", d, f)))
    out("  cstr  : " + repr(cstr(f)[:80]))
    for name, v in (("head", struct.unpack_from("<I", d, f)[0]),
                    ("tail", struct.unpack_from("<I", d, f+4)[0]),
                    ("f0", struct.unpack_from("<f", d, f)[0]),
                    ("f1", struct.unpack_from("<f", d, f+4)[0])):
        vv = v
        out("  %-4s -> VA 0x%06X  str=%r" % (name, vv+VA, cstr(vv+VA)[:60]) if 0 < vv < N else "  %-4s -> %r" % (name, vv))
