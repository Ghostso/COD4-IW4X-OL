import struct
p = r"CODOLServer\logs\full_image.bin"
d = open(p,'rb').read()
print("dump size", len(d))
magic = d[0:4]
print("magic", magic)
cnt = struct.unpack_from('<i', d, 4)[0]
print("region count", cnt)
off = 8
regs=[]
for i in range(cnt):
    b,s,o = struct.unpack_from('<III', d, off+i*12)
    regs.append((b,s,o))
    print("  region base=0x%08X size=0x%X off=0x%X" % (b,s,o))
# look at the first region's content
if regs:
    b,s,o = regs[0]
    data = d[o:o+64]
    print()
    print("first region head:", data.hex())
    print("as ascii:", ''.join(chr(c) if 32<=c<127 else '.' for c in data))
