import pefile, struct
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
def rd(va,n):
    o=pe.get_offset_from_rva(va-ib); return d[o:o+n]
print("=== jump table @0x10015688 (20 dwords) ===")
for i in range(20):
    v=struct.unpack_from("<I", rd(0x10015688,80), i*4)[0]
    print("   idx %2d (cmd %2d) -> 0x%08X"%(i, i+2, v))
print()
print("=== byte index table @0x100156ac (20 bytes) ===")
b=rd(0x100156ac,20)
print("   ", " ".join("%02x"%x for x in b))
