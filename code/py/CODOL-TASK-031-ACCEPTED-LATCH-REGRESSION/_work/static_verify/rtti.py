import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def u32(va): return struct.unpack_from("<I",d,va-BASE)[0]
def cstr(va,limit=200):
    o=va-BASE; end=d.find(b'\x00',o)
    return d[o:end].decode('latin1','replace')
for vt in (0xDC73A0,0xDC7840):
    col=u32(vt-4)
    print("vtable %08X  COL=%08X" % (vt,col))
    if 0x400000<=col<0xE65000:
        # COL layout (x86): signature, offset, cdOffset, pTypeDescriptor, pClassDescriptor(RTTIBaseClassArray)
        sig=u32(col); off=u32(col+4); cdoff=u32(col+8); ptd=u32(col+12)
        print("   sig=%08X off=%08X cdoff=%08X pTypeDescriptor=%08X" % (sig,off,cdoff,ptd))
        if 0x400000<=ptd<0xE65000:
            # TypeDescriptor: vftable ptr, spare, name[]
            name=cstr(ptd+8)
            print("   type name: %r" % name)
