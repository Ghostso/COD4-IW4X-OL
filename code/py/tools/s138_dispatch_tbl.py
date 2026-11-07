import struct,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read()
o=0x82e1458-VA
print("table @0x82e1458 (first 60 dwords):")
for i in range(60):
    v=struct.unpack_from("<I",d,o+i*4)[0]
    if v: print("  [%02d] 0x%08X"%(i,v))
