img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(img,"rb").read()
for va in (0xDE08C8, 0xDE08D8, 0xDE08E8, 0xDE0640):
    o = va - 0x400000
    if 0 <= o < len(d):
        s = d[o:o+48].split(b"\x00")[0]
        print("  0x%08X  %r" % (va, s))
    else:
        print("  0x%08X  OUT" % va)
