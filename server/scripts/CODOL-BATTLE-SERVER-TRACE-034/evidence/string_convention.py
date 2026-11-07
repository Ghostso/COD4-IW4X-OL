import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
print("file size 0x%X" % len(d))
print()
print("UNAMBIGUOUS STRING TEST (a wrong convention cannot produce the exact ASCII bytes):")
for va,expect in [(0xDC69B0,b"mmbook accepted"),(0xDC6800,b"mmstart sv_resetServer"),(0xDC6724,b"mmbook")]:
    off=va-BASE
    got=d[off:d.find(b'\x00',off)][:len(expect)]
    print("  VA %08X -> offset %08X -> %r  %s" % (va,off,got,"MATCH" if got==expect else "NO"))
    off2=va
    got2=d[off2:d.find(b'\x00',off2)][:len(expect)] if off2<len(d) else b"<OOR>"
    print("     alt (offset=VA)  %08X -> %r  %s" % (off2,got2,"MATCH" if got2==expect else "NO"))
print()
print("=> CONVENTION: file_offset = VA - 0x400000  (i.e. probe 'RVA' == VA-ImageBase)")
