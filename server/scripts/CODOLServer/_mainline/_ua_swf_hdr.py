import struct, zlib
d=open("ui_mp.ff","rb").read()
cands=[(0x73b281,b"FWS"),(0x9f72de,b"FWS"),(0x1549d2c,b"FWS"),(0x1a7cf49,b"FWS"),
       (0x1855a28,b"CWS"),(0x62c2b4,b"ZWS"),(0x7eebf4,b"ZWS"),(0x91e01c,b"ZWS"),(0xbcea53,b"ZWS"),
       (0x96091b,b"GFX"),(0xe95bc9,b"GFX"),(0x110b199,b"GFX"),(0xe3e4f1,b"gfx"),(0x1a02588,b"gfx")]
def swf_hdr(d,o):
    if d[o:o+3] not in (b"FWS",b"CWS",b"ZWS"): return None
    ver=d[o+3]
    # file length may be 4 bytes; if 0x3F then 8 bytes
    flen=struct.unpack_from("<I",d,o+4)[0]
    return ("SWF", d[o:o+3].decode(), ver, flen)
for off,m in cands:
    r=swf_hdr(d,off)
    if r:
        print("off 0x%07X  %s ver=%d filelen=%d" % (off, r[1], r[2], r[3]))
    else:
        # raw scan the region for readable strings
        seg=d[off:off+0x2000]
        import re
        ss=[x.group().decode("latin1") for x in re.finditer(rb"[\x20-\x7e]{6,}", seg)][:6]
        print("off 0x%07X  (非 SWF) 附近串: %s" % (off, ss))
