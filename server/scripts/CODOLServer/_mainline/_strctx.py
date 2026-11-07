import struct
exe = r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
data = open(exe,'rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe+6)[0]
opt = pe+24
imgbase = struct.unpack_from('<I', data, opt+28)[0]
secoff = opt + struct.unpack_from('<H', data, pe+20)[0]
secs=[]
for i in range(nsec):
    o = secoff + i*40
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, o+8)
    secs.append((vaddr, vsize, rawptr, rawsize))
def va2off(va):
    for vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= va < vaddr+rawsize:
            return rawptr + (va-vaddr)
    return None
base=0x95A4E8
o=va2off(base)
print("file off", hex(o))
print("dump around:")
for row in range(-64, 128, 16):
    b=data[o+row:o+row+16]
    print("  %08X  %s  %s" % (base+row, b.hex(), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))
