img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
for va in (0xD5A31C, 0xD5A0FC, 0xD5A0E8, 0xD59F08):
    o = va - BASE
    s = d[o:o+48].split(b"\x00")[0]
    print("0x%08X  %r" % (va, s))
