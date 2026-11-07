import struct,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read()
o=0x636f3c-VA
for i in range(47):
    v=struct.unpack_from("<I",d,o+i*4)[0]
    print("  type %2d -> 0x%08X"%(i,v))
