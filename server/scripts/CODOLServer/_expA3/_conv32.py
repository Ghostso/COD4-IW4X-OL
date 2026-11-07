import struct, zlib
def bmp2png(src,dst):
    d=open(src,"rb").read()
    off=struct.unpack_from("<I",d,10)[0]
    w=struct.unpack_from("<i",d,18)[0]; h=struct.unpack_from("<i",d,22)[0]
    bpp=struct.unpack_from("<H",d,28)[0]
    print("w",w,"h",h,"bpp",bpp)
    hh=abs(h); row=((w*bpp//8+3)//4)*4; px=bpp//8
    raw=bytearray()
    for y in range(hh):
        sy=(hh-1-y) if h>0 else y
        base=off+sy*row
        raw.append(0)
        for x in range(w):
            o=base+x*px
            b,g,r=d[o],d[o+1],d[o+2]
            raw+=bytes((r,g,b))
    def ck(t,dd):
        c=struct.pack(">I",len(dd))+t+dd
        return c+struct.pack(">I",zlib.crc32(t+dd)&0xffffffff)
    png=b"\x89PNG\r\n\x1a\n"+ck(b"IHDR",struct.pack(">IIBBBBB",w,hh,8,2,0,0,0))+ck(b"IDAT",zlib.compress(bytes(raw),6))+ck(b"IEND",b"")
    open(dst,"wb").write(png); print("wrote",dst,len(png))
bmp2png("after.png","after_real.png")
