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
    name = data[o:o+8].rstrip(b'\x00').decode('latin1')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, o+8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))
    print(f"{name:8s} va={vaddr:08X} vsize={vsize:08X} raw={rawptr:08X} rawsize={rawsize:08X}")
print("imagebase", hex(imgbase))
print()
print("0xCA8128 - imgbase =", hex(0xCA8128-imgbase))
