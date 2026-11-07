img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
for va in (0xDADDC4, 0xD5A114, 0xD5A32C):
    o = va - BASE
    s = d[o:o+48].split(b"\x00")[0]
    print("0x%08X  %r" % (va, s))
